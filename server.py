import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Literal

from agents import Agent, Runner, AsyncOpenAI, ModelSettings, OpenAIChatCompletionsModel
from tools import get_diamond_holders

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# --- FastAPI app ---
app = FastAPI()

# --- Определяем базовый URL и API ключ ---
def get_api_config():
    # Проверяем, какой API использовать
    api_type = os.getenv("API_TYPE", "ollama").lower()  # По умолчанию используем Ollama
    
    if api_type == "openai":
        # Используем OpenAI API
        base_url = "https://api.openai.com/v1"
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI API")
        model = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    else:
        # Используем Ollama
        is_docker = os.path.exists('/.dockerenv')
        if is_docker:
            base_url = "http://host.docker.internal:11434/v1"
        else:
            base_url = "http://localhost:11434/v1"
        api_key = "dummy-key"  # Не используется для Ollama
        model = os.getenv("MODEL_NAME", "llama3.1")
    
    print(f"Using API: {api_type}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    
    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model
    }

# --- Агент и модель ---
api_config = get_api_config()

external_client = AsyncOpenAI(
    base_url = api_config["base_url"],
    api_key = api_config["api_key"]
)

agent = Agent(
    name="Diamond Holder Agent",
    instructions="""
You are a blockchain analytics agent that provides token holder information in a clear, formatted way.

INSTRUCTION 1: CHECK TOKEN ADDRESS
If the user did not provide a token address, respond with this exact message (do not include the markdown code block markers):

"
# Token Address Required
To analyze diamond holders, please provide a valid token address from one of the supported networks.

## How to Use
You can customize your query with these parameters:
- Number of holders to show (default: 10)
- Days since last balance update (default: 30)

## Example Queries
- "Show top 5 diamond holders of [token_address] with no updates in last 7 days"
- "Get top 20 diamond holders of [token_address]" (uses default 30 days)
- "Give me diamond holders of [token_address]" (uses default settings)

## Supported Networks
- Ethereum (ETH)
- Binance Smart Chain (BSC)
- Arbitrum
- Base
"

INSTRUCTION 2: HANDLE ERRORS AND EMPTY DATA
If the tool returns an error message (starts with "Error:"), respond with this exact message:

"
# Error Occurred
[ERROR_MESSAGE]

Please try your request again. If the error persists, try:
- Verifying the token address
- Checking if the token is supported
- Using a different network
"

If the tool returns empty data (no holders found), respond with this exact message:

"
# No Diamond Holders Found
No holders matching your criteria were found. Try adjusting your search parameters:
- Increase the number of days since last update
- Try a different token address
- Check if the token is active on the selected network
"

INSTRUCTION 3: FORMAT HOLDER DATA
When you receive valid data about diamond holders, format your response exactly like this (do not include the markdown code block markers):

"
# Token Information
- **Token Address**: [Address]
- **Name**: [Token Name]
- **Symbol**: [Token Symbol]

# Top Diamond Holders
| Address | Balance | Last Updated |
|---------|---------|--------------|
| [Address] | [Balance] | [Date] |

# Query Parameters
- **Days Since Last Update**: [Days]
- **Result Limit**: [Limit]
"

INSTRUCTION 4: GENERAL RULES
- Always format your responses in markdown
- Do not include any code block markers (```) in your responses
- Do not explain the data — just display it in the formatted structure
- Replace all placeholders (like [Token Name], [Address], etc.) with actual data
- Replace [ERROR_MESSAGE] with the actual error message from the tool
- If the address validation fails, show the error message and suggest using a valid Ethereum address
""",
    model=OpenAIChatCompletionsModel(
        model=api_config["model"],
        openai_client=external_client
    ),
    model_settings=ModelSettings(temperature=0.5),
    tools=[get_diamond_holders]
)

async def test_model_connection():
    try:
        print("\n=== Testing model connection ===")
        print(f"MODEL_BASE_URL: {api_config['base_url']}")  # Используем функцию вместо os.getenv
        print(f"MODEL_NAME: {api_config['model']}")  # Добавим значение по умолчанию
        
        test_result = await Runner.run(
            starting_agent=agent,
            input="Say 'Hello, I am working!'"
        )
        
        print("\nModel response:")
        print(test_result.final_output)
        print("=== Test completed successfully ===\n")
        
    except Exception as e:
        print("\n=== Model connection test failed ===")
        print(f"Error: {str(e)}")
        import traceback
        print("Traceback:")
        print(traceback.format_exc())
        print("================================\n")

# --- OpenAI совместимые схемы ---
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.5
    max_tokens: Optional[int] = 2048

# --- /v1/chat/completions ---
@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    last_user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), None)
    if not last_user_msg:
        return JSONResponse(
            status_code=400,
            content={"error": "No user message provided."}
        )

    try:
        result = await Runner.run(
            starting_agent=agent,
            input=last_user_msg
        )

        result_text = str(result.final_output) 

        print(f"RESULT:\n\n{result}\n\n")
        return JSONResponse(
            status_code=200,
            content={
                "id": "chatcmpl-agent-001",
                "object": "chat.completion",
                "created": int(os.times().elapsed),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        )


    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# --- /v1/models ---
@app.get("/v1/models")
def list_models():
    return JSONResponse(
        content={
            "object": "list",
            "data": [
                {
                    "id": api_config["model"],
                    "object": "model",
                    "owned_by": "you"
                }
            ]
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# --- OPTIONS /v1/models (если нужно явно) ---
@app.options("/v1/models")
def options_models():
    return Response(status_code=200)

@app.get("/v1/chats/models")
def list_models_alias():
    return JSONResponse(
        content={
            "object": "list",
            "data": [
                {
                    "id": api_config["model"],
                    "object": "model",
                    "owned_by": "you"
                }
            ]
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.options("/v1/chats/models")
def options_chats_models():
    return Response(status_code=200)

# @app.on_event("startup")
# async def startup_event():
#     await test_model_connection()
