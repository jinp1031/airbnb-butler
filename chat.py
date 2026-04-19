# chat.py
from openai import OpenAI
from config import MODEL
from tools import TOOL_SCHEMAS, handle_tool_calls

client = OpenAI()

SYSTEM_PROMPT = """你是一个专业的 Airbnb 房东助手。

你的核心准则：
1. 只要用户询问任何关于"房态"、"订单"、"谁住"、"有没有空"等涉及数据库的问题，你必须【第一步】先调用 sync_db 工具。
2. 只有在同步成功后，你才能【第二步】调用 get_dates 获取具体数据。
3. 绝对禁止在未同步的情况下直接使用数据库旧数据回答用户。"""

def chat(message: str, history: list):
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + [{"role": h["role"], "content": h["content"]} for h in history]
        + [{"role": "user", "content": message}]
    )

    # Tool call 阶段：不流式，先把工具跑完
    response = client.chat.completions.create(
        model=MODEL, messages=messages, tools=TOOL_SCHEMAS
    )

    while response.choices[0].finish_reason == "tool_calls":
        ai_msg = response.choices[0].message
        messages.append(ai_msg)

        # 给用户一个同步中的提示（可选，让界面不显得卡住）
        yield "⏳ 正在同步房态数据..."

        messages.extend(handle_tool_calls(ai_msg))
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS
        )

    # 最终回复阶段：流式输出
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_SCHEMAS,
        stream=True
    )

    partial = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            partial += delta
            yield partial