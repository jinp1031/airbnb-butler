# sync.py
import sqlite3
import requests
from icalendar import Calendar
from datetime import datetime
from config import ROOMS
from db import DB

def sync_db() -> str:
    if not ROOMS:
        return "同步失败：没有任何有效的房间配置"

    print("\n🚀 开始同步房态数据...")
    total_synced = 0
    today_str = datetime.now().strftime("%Y-%m-%d")

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        for room_name, url in ROOMS.items():
            print(f"🌍 正在拉取 [{room_name}]...")
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                cal = Calendar.from_ical(response.text)

                active_order_ids = []
                room_count = 0

                for component in cal.walk("vevent"):
                    summary = str(component.get("summary", ""))
                    if "Reserved" in summary:
                        label = "Reserved (真实订单)"
                    elif "Airbnb" in summary or "Blocked" in summary:
                        label = "Blocked (系统锁房)"
                    else:
                        continue

                    uid = str(component.get("uid"))
                    check_in = component.get("dtstart").dt.strftime("%Y-%m-%d")
                    check_out = component.get("dtend").dt.strftime("%Y-%m-%d")

                    active_order_ids.append(uid)
                    cursor.execute("""
                        INSERT OR REPLACE INTO bookings
                            (room_name, check_in, check_out, guest_name, order_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (room_name, check_in, check_out, label, uid))
                    room_count += 1
                    total_synced += 1

                # Mark & Sweep 
                if active_order_ids:
                    placeholders = ",".join(["?"] * len(active_order_ids))
                    cursor.execute(f"""
                        DELETE FROM bookings
                        WHERE room_name = ?
                          AND check_out >= ?
                          AND order_id NOT IN ({placeholders})
                    """, [room_name, today_str] + active_order_ids)
                    deleted = cursor.rowcount
                    if deleted > 0:
                        print(f"  🧹 清理了 {deleted} 条幽灵订单")

                print(f"  ✅ {room_name} 完成，入库 {room_count} 条")

            except requests.RequestException as e:
                print(f"  ❌ {room_name} 网络拉取失败: {e}")
                return f"同步失败：{room_name} 无法连接（{e}）"
            except Exception as e:
                print(f"  ❌ {room_name} 解析失败: {e}")
                return f"同步失败：{room_name} 数据解析出错（{e}）"

        conn.commit()

    return f"🎉 同步完成，共刷新 {total_synced} 条订单"