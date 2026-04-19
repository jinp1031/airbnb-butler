import gradio as gr
from db import init_db
from chat import chat

init_db()

gr.ChatInterface(
    fn=chat,
    type="messages",
    title="🏡 Airbnb 管家",
    examples=[
        "查一下所有房间 4 月份的订单",
        "看看 1 号房 3 月份的情况",
        "查 1 号房 3 月 和 3 号房 4 月 的排期",
    ],
).launch()