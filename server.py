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

# --- Определяем базовый URL для Ollama ---
def get_ollama_base_url():
    # Проверяем, запущены ли мы в контейнере
    is_docker = os.path.exists('/.dockerenv')
    
    if is_docker:
        # В контейнере используем host.docker.internal
        base_url = "http://host.docker.internal:11434/v1"  # Добавляем /v1 для OpenAI-совместимого API
    else:
        # Локально используем localhost
        base_url = "http://localhost:11434/v1"  # Добавляем /v1 для OpenAI-совместимого API
    
    print(f"Using Ollama base URL: {base_url}")
    return base_url

# --- Агент и модель ---
external_client = AsyncOpenAI(
    base_url = get_ollama_base_url(),  # Используем функцию для определения URL
    api_key="dummy-key"  # Не используется, просто заглушка
)

print("Model base URL:", get_ollama_base_url())
print("Model name:", os.getenv("MODEL_NAME", "llama3.1"))

agent = Agent(
    name="Diamond Holder Agent",
    instructions="""
You are a blockchain analytics agent. You respond with token holder information.
You have access to a tool that retrieves and formats data about 'diamond holders' of a token. 
If the tool is used, simply return the formatted output it gives without modifying it. 
The result should contain all the sections:
- Token Info (Name, Symbol)
- Top Diamond Holders (Address, Balance, Last Updated)
- Query Parameters (Token Address, Days Since Last Update, Result Limit)
Do not explain the data — just display the result as-is to the user.
""",
    model=OpenAIChatCompletionsModel(
        model=os.getenv("MODEL_NAME", "llama3.1"),  # Используем установленную модель
        openai_client=external_client
    ),
    model_settings=ModelSettings(temperature=0.5),
    tools=[get_diamond_holders]
)

async def test_model_connection():
    try:
        print("\n=== Testing model connection ===")
        print(f"MODEL_BASE_URL: {get_ollama_base_url()}")  # Используем функцию вместо os.getenv
        print(f"MODEL_NAME: {os.getenv('MODEL_NAME', 'llama3.1')}")  # Добавим значение по умолчанию
        
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
    return {
        "object": "list",
        "data": [
            {
                "id": "llama3.1",
                "object": "model",
                "owned_by": "you"
            }
        ]
    }

# --- OPTIONS /v1/models (если нужно явно) ---
@app.options("/v1/models")
def options_models():
    return Response(status_code=200)

@app.get("/v1/chats/models")
def list_models_alias():
    return {
        "object": "list",
        "data": [
            {
                "id": "llama3.1",
                "object": "model",
                "owned_by": "you"
            }
        ]
    }

@app.options("/v1/chats/models")
def options_chats_models():
    return Response(status_code=200)

# @app.on_event("startup")
# async def startup_event():
    # await test_model_connection()
