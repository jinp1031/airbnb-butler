#import
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import sqlite3
import requests
from icalendar import Calendar
from datetime import datetime

#Initialization
load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')
ROOM1_URL=os.getenv('ROOM_1_URL')
ROOM2_URL=os.getenv('ROOM_2_URL')
ROOM3_URL=os.getenv('ROOM_3_URL')

required_configs={
    "OpenAI Key": openai_api_key,
    "Room #1 link": ROOM1_URL,
    "Room #2 link": ROOM2_URL,
    "Room #3 link": ROOM3_URL
}

missing_configs= [name for name, value in required_configs.items() if not value]

if not missing_configs:
    print(f"initialization successful")
else:
    error_details=','.join(missing_configs)
    print(f'missing configs as follow [{error_details}]')


MODEL = "gpt-4o-mini"
openai = OpenAI()

#database
DB="airbnb_guests.db"
with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS bookings (order_id TEXT PRIMARY KEY, guest_name TEXT, room_name TEXT, check_in TEXT, check_out TEXT)')
    conn.commit() 

system_prompt = """你是一个专业的 Airbnb 房东助手。
你的核心准则：
1. 只要用户询问任何关于“房态”、“订单”、“谁住”、“有没有空”等涉及数据库的问题，你必须【第一步】先调用 `sync_db` 工具。
2. 只有在同步成功后，你才能【第二步】调用 `get_dates` 获取具体数据。
3. 绝对禁止在未同步的情况下直接使用数据库旧数据回答用户。"""

def sync_db():
    print("\n🚀 [系统动作] 开始抓取并同步房态数据...")
    raw_rooms = {
        "Room #1": ROOM1_URL,
        "Room #2": ROOM2_URL,
        "Room #3": ROOM3_URL
    }
    active_rooms = {name: url for name, url in raw_rooms.items() if url}

    if not active_rooms:
        return "同步失败：没有任何有效的房间配置。"

    total_synced = 0 # 记录总共入库了多少条
    today_str = datetime.now().strftime('%Y-%m-%d') # 获取今天的日期

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        
        for room_name, url in active_rooms.items():
            print(f"🌍 正在拉取 [{room_name}] 的日历...")
            
            try:
                response = requests.get(url)
                response.raise_for_status()
                cal = Calendar.from_ical(response.text)
                
                room_event_count = 0
                # 🌟 新增：用来收集存活订单号的“点名册”
                active_order_ids = [] 
                
                for component in cal.walk('vevent'):
                    summary = str(component.get('summary', ''))
                    
                    if "Reserved" in summary:
                        status_label = "Reserved (真实订单)"
                    elif "Airbnb" in summary or "Blocked" in summary:
                        status_label = "Blocked (系统锁房)"
                    else:
                        continue

                    start_date = component.get('dtstart').dt.strftime('%Y-%m-%d')
                    end_date = component.get('dtend').dt.strftime('%Y-%m-%d')
                    uid = str(component.get('uid'))
                        
                    # 1. 记录到点名册中
                    active_order_ids.append(uid)
                        
                    # 2. 执行常规的 Upsert (更新/插入)
                    cursor.execute('''
                            INSERT OR REPLACE INTO bookings (room_name, check_in, check_out, guest_name, order_id)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (room_name, start_date, end_date, status_label, uid))
                        
                    room_event_count += 1
                    total_synced += 1
                        
                # 🌟🌟 核心魔法：大清洗 (Mark & Sweep) 🌟🌟
                if active_order_ids:
                    # 动态生成 SQL 中的 (?, ?, ?) 占位符
                    placeholders = ','.join(['?'] * len(active_order_ids))
                    
                    # 清理逻辑：
                    # 1. 是当前房间的订单
                    # 2. 且退房日期在今天之后 (我们保留历史已完成的订单记录不删)
                    # 3. 且订单号不在刚才的“点名册”里
                    delete_sql = f'''
                        DELETE FROM bookings 
                        WHERE room_name = ? 
                          AND check_out >= ? 
                          AND order_id NOT IN ({placeholders})
                    '''
                    # 执行删除，传入参数：[房间名, 今天的日期, 存活订单1, 存活订单2...]
                    cursor.execute(delete_sql, [room_name, today_str] + active_order_ids)
                    
                    # 获取刚刚删掉了几条“幽灵订单”
                    deleted_count = cursor.rowcount
                    if deleted_count > 0:
                        print(f"   🧹 清理了 {deleted_count} 条已被取消的幽灵订单。")

                print(f"   ✅ {room_name} 处理完毕，入库 {room_event_count} 条记录。")

            except Exception as e:
                print(f"   ❌ {room_name} 抓取失败: {e}")
        
        conn.commit() 

    return f"🎉 同步完成！刷新了 {total_synced} 条订单。"



def get_dates(room_name, target_month):
    print(f"🤖 [AI 正在偷偷查库] 房间: {room_name}, 月份: {target_month}")

    raw_room = str(room_name).lower().replace(" ", "").replace("#", "")
    room_mapping = {
        "1": "Room #1", "room1": "Room #1",
        "2": "Room #2", "room2": "Room #2",
        "3": "Room #3", "room3": "Room #3"
    }
    standard_room = room_mapping.get(raw_room, str(room_name))
    standard_month = str(target_month).zfill(2)
    formatted_month = f"-{standard_month}-"
    
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT guest_name, check_in, check_out 
            FROM bookings 
            WHERE room_name = ? AND check_in LIKE ?
            ORDER BY check_in ASC
        ''', (standard_room, f'%{formatted_month}%'))

        results = cursor.fetchall()
        if not results:
            return f"no results for: {room_name} at {target_month}"

        order_count = 1
        info = f"found {len(results)} orders: "
        for row in results:
            guest, check_in, check_out = row
            if "Blocked" in guest:
                info += f"⛔ 锁房/不可用：{check_in} 至 {check_out} (此期间并非真实订单，而是房间被冻结)。\n"
            else:
                info += f"✅ 真实订单{order_count}：{check_in} 入住，{check_out} 退房。\n"
                order_count += 1
        
    return info

sync_function = {
    "name": "sync_db",
    "description": "【前置必选项】当用户询问任何关于房态、排期、订单的问题时，【必须第一步】调用此工具拉取最新数据。不需要任何参数。"
}
date_function = {
    "name": "get_dates",
            "description": "从本地数据库检索订单。注意：此工具数据可能滞后，查询前请务必确认已运行过 sync_db。",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_name": {
                        "type": "string",
                        "description": "必须是 'Room #1', 'Room #2', 或 'Room #3' 之一。"
                    },
                    "target_month": {
                        "type": "string",
                        "description": "提取用户意图中的月份。无论用户使用哪种语言（中文'三月'、西班牙语'marzo'），你都必须将其转换为 1 到 12 的纯数字。例如:1月输出 1,11月输出 11。"
                    }
                },
                "required": ["room_name", "target_month"],
                "additionalProperties": False
            }
        }

tools = [{"type": "function", "function": sync_function},{"type": "function", "function": date_function}]

def handle_tool_calls_and_return_results(message):
    print(f"开始调用工具")
    tool_responses = []
    sync_already_done = False
    sync_cached_result = ""

    for tool_call in message.tool_calls:
        tool_name = tool_call.function.name
        args_str = tool_call.function.arguments
        arguments = json.loads(args_str) if args_str else {}

        if tool_name == "sync_db":
            if not sync_already_done:
                sync_cached_result = sync_db()
                sync_already_done = True
            else:
                print(f"synced to the db already")
            response = sync_cached_result
        elif tool_name == "get_dates":
            target_month = arguments.get('target_month')
            room_name = arguments.get('room_name')
            response = get_dates(room_name,target_month)
        else:
            response = "error: unknown tools called"

        tool_responses.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": str(response)
        })

        
    return tool_responses


def chat(message,history):
    history = [{"role":h["role"], "content":h["content"]} for h in history]
    messages = [{"role": "system", "content": system_prompt}] + history +[{"role": "user", "content": message}]

    response = openai.chat.completions.create(model=MODEL, messages=messages, tools=tools)

    while response.choices[0].finish_reason=="tool_calls":
        ai_msg = response.choices[0].message
        messages.append(ai_msg)
        responses = handle_tool_calls_and_return_results(ai_msg)
        messages.extend(responses)
        response = openai.chat.completions.create(model=MODEL, messages=messages, tools=tools)
    

    reply = response.choices[0].message.content

    return reply

gr.ChatInterface(fn=chat,type="messages",title="🏡 Airbnb管家",examples=[
        "查一下所有房间4月份的订单",
        "📅 看看 1号房 3月份的情况",
        "🚀 帮我查查 1号房 3月 和 3号房 4月 的排期"
    ]).launch()