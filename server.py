import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Literal
import time
import uuid
import socket

from agents import Agent, Runner, AsyncOpenAI, ModelSettings, OpenAIChatCompletionsModel
from tools import get_diamond_holders

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

# --- FastAPI app ---
app = FastAPI()

# Добавляем middleware для отключения кэширования
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

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
        "model": model,
        "timestamp": time.time(),  # Добавляем временную метку
        "request_id": str(uuid.uuid4())  # Добавляем уникальный идентификатор
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
    # Обновляем конфигурацию при каждом запросе
    current_config = get_api_config()
    return JSONResponse(
        content={
            "object": "list",
            "data": [
                {
                    "id": current_config["model"],
                    "object": "model",
                    "owned_by": "you",
                    "timestamp": current_config["timestamp"],
                    "request_id": current_config["request_id"]
                }
            ]
        }
    )

# --- OPTIONS /v1/models (если нужно явно) ---
@app.options("/v1/models")
def options_models():
    return Response(status_code=200)

@app.get("/v1/chats/models")
def list_models_alias():
    # Обновляем конфигурацию при каждом запросе
    current_config = get_api_config()
    return JSONResponse(
        content={
            "object": "list",
            "data": [
                {
                    "id": current_config["model"],
                    "object": "model",
                    "owned_by": "you",
                    "timestamp": current_config["timestamp"],
                    "request_id": current_config["request_id"]
                }
            ]
        }
    )

@app.options("/v1/chats/models")
def options_chats_models():
    return Response(status_code=200)

# Включаем тестовое подключение при старте
@app.on_event("startup")
async def startup_event():
    await test_model_connection()

if __name__ == "__main__":
    import uvicorn
    port = find_free_port()
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
