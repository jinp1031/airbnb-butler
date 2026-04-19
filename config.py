# config.py
import os
from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"

ROOMS = {}
i = 1
while True:
    url = os.getenv(f"ROOM_{i}_URL")
    if not url:
        break
    ROOMS[f"Room #{i}"] = url
    i += 1

missing = []
if not OPENAI_API_KEY:
    missing.append("OPENAI_API_KEY")
if not ROOMS:
    missing.append("至少一个 ROOM_*_URL")

if missing:
    print(f"⚠️  缺少配置: {', '.join(missing)}")
else:
    print(f"✅ 初始化成功，共加载 {len(ROOMS)} 个房间")