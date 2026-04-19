# db.py
import sqlite3

DB = "airbnb_guests.db"

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                order_id   TEXT PRIMARY KEY,
                guest_name TEXT,
                room_name  TEXT,
                check_in   TEXT,
                check_out  TEXT
            )
        """)
        conn.commit()

def get_dates(room_name: str, target_month: str) -> str:
    raw = str(room_name).lower().replace(" ", "").replace("#", "")
    mapping = {
        "1": "Room #1", "room1": "Room #1",
        "2": "Room #2", "room2": "Room #2",
        "3": "Room #3", "room3": "Room #3",
    }
    standard_room = mapping.get(raw, room_name)
    formatted_month = f"-{str(target_month).zfill(2)}-"

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT guest_name, check_in, check_out FROM bookings
            WHERE room_name = ? AND check_in LIKE ?
            ORDER BY check_in ASC
        """, (standard_room, f"%{formatted_month}%"))
        results = cursor.fetchall()

    if not results:
        return f"没有找到 {room_name} 在 {target_month} 月的订单"

    info = f"共找到 {len(results)} 条记录：\n"
    order_count = 1
    for guest, check_in, check_out in results:
        if "Blocked" in guest:
            info += f"⛔ 锁房：{check_in} 至 {check_out}\n"
        else:
            info += f"✅ 订单 {order_count}：{check_in} 入住，{check_out} 退房\n"
            order_count += 1
    return info