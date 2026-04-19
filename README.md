# 🏡 Airbnb Butler

An AI-powered property management assistant for short-term rental hosts. Ask questions in natural language — the butler syncs your latest booking data from Airbnb's iCal feed in real time and answers instantly.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai&logoColor=white)
![Gradio](https://img.shields.io/badge/Gradio-UI-orange?logo=gradio&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local--DB-003B57?logo=sqlite&logoColor=white)

---

## ✨ Features

- **Natural language queries** — Ask in Chinese, English, or any language
- **Real-time iCal sync** — Pulls live booking data directly from Airbnb before every answer
- **Ghost booking cleanup** — Automatically removes cancelled reservations using a Mark & Sweep strategy
- **Streaming responses** — Replies stream word-by-word for a smooth chat experience
- **Multi-room support** — Manage unlimited rooms via environment variables, no code changes needed
- **Blocked vs. reserved detection** — Distinguishes real guest bookings from system-locked dates

---

## 🏗️ Architecture

```
airbnb-butler/
├── app.py          # Entry point — launches Gradio UI
├── chat.py         # Agentic loop with streaming output
├── tools.py        # OpenAI tool schemas + tool call dispatcher
├── sync.py         # iCal fetching, parsing, and DB sync
├── db.py           # SQLite init and booking queries
├── config.py       # Environment variable loading + room configuration
├── requirements.txt
└── .env.example
```

### How it works

```
User question
     │
     ▼
chat.py — builds message history, calls OpenAI
     │
     ▼ (if tool_calls)
tools.py — dispatches to sync_db or get_dates
     │
     ├──► sync.py — fetches iCal → writes to SQLite
     │
     └──► db.py   — queries bookings by room + month
     │
     ▼
Streaming reply back to Gradio UI
```

The LLM is instructed to **always sync first** before querying — ensuring answers are never based on stale data.

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/jinp1031/airbnb-butler.git
cd airbnb-butler
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
OPENAI_API_KEY=sk-...

# Add as many rooms as you need — no code changes required
ROOM_1_URL=https://www.airbnb.com/calendar/ical/YOUR_LISTING_ID_1.ics?s=...
ROOM_2_URL=https://www.airbnb.com/calendar/ical/YOUR_LISTING_ID_2.ics?s=...
ROOM_3_URL=https://www.airbnb.com/calendar/ical/YOUR_LISTING_ID_3.ics?s=...
```

> **How to get your iCal URL:** Airbnb → Manage listing → Availability → Export calendar → Copy link

### 4. Run

```bash
python app.py
```

Open your browser at `http://localhost:7860`

---

## 💬 Example Queries

| You say | What happens |
|---|---|
| `查一下所有房间 4 月份的订单` | Syncs all rooms, returns April bookings |
| `1 号房 3 月有空吗` | Syncs + shows March schedule for Room 1 |
| `查 1 号房 3 月 和 3 号房 4 月 的排期` | Parallel query across two rooms and months |
| `March bookings for room 2` | Works in English too |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| AI integration | OpenAI Tool Calling (function calling) |
| iCal parsing | `icalendar` library |
| Database | SQLite (local, zero-config) |
| UI | Gradio `ChatInterface` with streaming |
| Config | `python-dotenv` |

---

## 🧠 Technical Highlights

**Agentic tool calling loop**
The assistant uses OpenAI's function calling API in a `while finish_reason == "tool_calls"` loop, correctly handling multi-step reasoning — sync first, then query.

**Mark & Sweep ghost booking cleanup**
After each iCal sync, the app compares active order IDs against the database and deletes any future bookings that no longer appear in the feed (i.e. cancelled reservations), keeping data fresh without manual intervention.

**Streaming with tool calls**
Tool execution (sync + DB query) runs non-streaming first. Once tools are resolved, the final reply is streamed token-by-token via `stream=True`, giving users real-time feedback without blocking.

**Dynamic room configuration**
Rooms are loaded at startup by scanning `ROOM_1_URL`, `ROOM_2_URL`, ... `ROOM_N_URL` from the environment. Adding a new property requires only one line in `.env`.

---

## 📋 Requirements

```
openai
gradio
python-dotenv
requests
icalendar
```

---

## 📁 .env.example

```env
OPENAI_API_KEY=your_openai_api_key_here

ROOM_1_URL=your_airbnb_ical_url_for_room_1
ROOM_2_URL=your_airbnb_ical_url_for_room_2
ROOM_3_URL=your_airbnb_ical_url_for_room_3
```

---

## 🗺️ Roadmap

- [ ] Deploy to Hugging Face Spaces
- [ ] WhatsApp / email notification when new booking detected
- [ ] Multi-language guest message templates
- [ ] Booking conflict detection across rooms
- [ ] Weekly occupancy summary report

---

## 👤 Author

Built by [@jinp1031](https://github.com/jinp1031)
