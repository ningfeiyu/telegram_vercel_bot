from flask import Flask, request, jsonify
import os
import requests
from openai import OpenAI
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NVIDIA_NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "meta/llama3-70b-instruct")

# 初始化 Nvidia NIM 客户端
client = None
if NVIDIA_NIM_API_KEY:
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_NIM_API_KEY
    )

def send_telegram_message(chat_id, text):
    """专门用来回复消息给 Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

@app.route('/', methods=['GET'])
def index():
    return "🚀 Vercel Webhook for Telegram Bot is active!"

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """接收 Telegram 推送过来的按需 Webhook 请求"""
    if not TELEGRAM_TOKEN or not NVIDIA_NIM_API_KEY:
        return jsonify({"error": "Missing environment variables"}), 500

    update = request.get_json()
    if not update:
        return jsonify({"status": "ignored"}), 200

    # 提取聊天ID和用户发送的文本 (忽略非文本内容)
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"]
        
        # 如果是 /start 命令
        if user_text.startswith('/start'):
            send_telegram_message(chat_id, "👋 你好！我是搭载 Nvidia NIM 的 AI 助手。由于我运行在 Vercel Serverless 上，响应极快且永远在线，请直接问我任何问题吧！")
            return jsonify({"status": "ok"}), 200

        try:
            # 向长时调用的 Nvidia NIM 获取回复
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个非常有用的中文 AI 助手。请直接、清晰、专业地回答用户的问题。"},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            reply = completion.choices[0].message.content
            # 把拿到的回复发回给用户
            send_telegram_message(chat_id, reply)
            
        except Exception as e:
            logging.error(f"Error calling Nvidia API: {e}")
            send_telegram_message(chat_id, f"抱歉，大脑短暂短路了：{str(e)}")

    return jsonify({"status": "ok"}), 200

# 仅限本地测试用，Vercel 实际运行不需要这个
if __name__ == '__main__':
    app.run(port=3000)
