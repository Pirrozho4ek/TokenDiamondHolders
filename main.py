import os
from dotenv import load_dotenv
load_dotenv()
from agents import Agent, Runner, AsyncOpenAI, ModelSettings, OpenAIChatCompletionsModel
from tools import get_diamond_holders, format_diamond_holders_result, _fetch_diamond_holders_data

# ⚙️ Настройки подключения к локальному LLM (Ollama, LM Studio и т.п.)
external_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="dummy-key"
)

# 🧠 Агент с инструкциями
agent = Agent(
    name="Diamond Holder Agent",
    instructions="""
You are a blockchain analytics agent. You help users analyze token holders on EVM-based blockchains.

If you use the `get_diamond_holders` tool, you MUST return the result of this tool AS IS, without any changes, explanations, or additional text. Do NOT add any summary, introduction, or comments. Just output the tool's result directly.

If you don't have enough information or a tool wasn't called, respond with a helpful message or follow-up question.
""",
    model=OpenAIChatCompletionsModel(
        model=os.getenv("MODEL_NAME"),  
        openai_client=external_client,
    ),
    model_settings=ModelSettings(temperature=0.5),
    tools=[
        get_diamond_holders
    ]
)

if __name__ == "__main__":
    user_prompt = "Who are the top 10 diamond holders of the token 0x12652c6d93fdb6f4f37d48a8687783c782bb0d10?"

    result = Runner.run_sync(
        starting_agent=agent,
        input=user_prompt
    )

    print(result)
    # raw_result = _fetch_diamond_holders_data("0x12652c6d93fdb6f4f37d48a8687783c782bb0d10")
    # print(raw_result)
    # print(format_diamond_holders_result(raw_result))
