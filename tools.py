# tools.py
import json
from sync import sync_db
from db import get_dates

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "sync_db",
            "description": "【前置必选项】当用户询问任何关于房态、排期、订单的问题时，必须第一步调用此工具拉取最新数据。不需要任何参数。",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dates",
            "description": "从本地数据库检索订单。注意：查询前请务必确认已运行过 sync_db。",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_name": {
                        "type": "string",
                        "description": "必须是 'Room #1'、'Room #2' 或 'Room #3' 之一",
                    },
                    "target_month": {
                        "type": "string",
                        "description": "将用户意图中的月份转换为 1–12 的纯数字",
                    },
                },
                "required": ["room_name", "target_month"],
                "additionalProperties": False,
            },
        },
    },
]

def handle_tool_calls(message) -> list:
    responses = []
    sync_done = False
    sync_result = ""

    for tool_call in message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

        if name == "sync_db":
            if not sync_done:
                sync_result = sync_db()
                sync_done = True
            result = sync_result
        elif name == "get_dates":
            result = get_dates(args.get("room_name"), args.get("target_month"))
        else:
            result = f"未知工具：{name}"

        responses.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": name,
            "content": str(result),
        })

    return responses