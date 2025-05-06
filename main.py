import os
import requests
import json
import threading
import time
import sys
from flask import Flask, request
from zoneinfo import ZoneInfo
import datetime

app = Flask(__name__)

TOKEN = os.environ['TOKEN']
URL = f'https://api.telegram.org/bot{TOKEN}/'
SCHEDULE_FILE = 'schedule.json'
CHAT_ID = None

START_TIME = time.time()
MAX_RUNTIME_MIN = 29400  # 490 ชั่วโมง
NOTIFY_THRESHOLD_MIN = 30  # เตือนเมื่อเหลือ 30 นาที

# ========= ฟังก์ชัน =========
def send_message(chat_id, text):
    requests.post(URL + 'sendMessage', data={'chat_id': chat_id, 'text': text})

def load_schedule():
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except:
        return []

def save_schedule(lst):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(lst, f, ensure_ascii=False)

def add_schedule(time_str, message):
    lst = load_schedule()
    lst.append({'time': time_str, 'message': message})
    save_schedule(lst)

def check_and_notify():
    now = datetime.datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%H:%M')
    lst = load_schedule()
    for event in lst:
        if event['time'] == now and CHAT_ID:
            send_message(CHAT_ID, f"🔔 แจ้งเตือน: {event['message']}")

# ========= ตรวจจับเวลาและปิดอัตโนมัติ =========
def monitor_runtime():
    global CHAT_ID
    warned = False
    while True:
        runtime_min = (time.time() - START_TIME) / 60
        remaining = MAX_RUNTIME_MIN - runtime_min

        if remaining < NOTIFY_THRESHOLD_MIN and not warned:
            if CHAT_ID:
                send_message(CHAT_ID, f"[ ⚠️ ] 9CharnBot : ใกล้หมดเวลาแล้ว เหลือประมาณ {int(remaining)} นาที")
            warned = True

        if runtime_min >= MAX_RUNTIME_MIN:
            if CHAT_ID:
                send_message(CHAT_ID, "[ ⛔️ ] 9CharnBot : บอทปิดตัวเพื่อประหยัดเวลา (ครบ 490 ชั่วโมง)")
            print("⏹️ Shutdown: Max runtime reached.")
            sys.exit()

        time.sleep(60)

threading.Thread(target=monitor_runtime, daemon=True).start()

# ========= Webhook =========
@app.route('/')
def home():
    return '✅ Bot Webhook is active'

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    global CHAT_ID
    data = request.get_json()
    if 'message' in data:
        msg = data['message']
        CHAT_ID = msg['chat']['id']
        text = msg.get('text', '')
        if text == '/start':
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot ใช้งานผ่าน Webhook\nใช้ /add /list /remove ได้เลย")
        elif text.startswith('/add '):
            try:
                parts = text[5:].split(' ', 1)
                t, m = parts[0], parts[1]
                datetime.datetime.strptime(t, '%H:%M')
                add_schedule(t, m)
                send_message(CHAT_ID, f"✅ เพิ่มงาน: {t} → {m}")
            except:
                send_message(CHAT_ID, "❌ รูปแบบไม่ถูกต้อง /add HH:MM ข้อความ")
        elif text == '/list':
            lst = load_schedule()
            if lst:
                lines = [f"{i+1}. {e['time']} → {e['message']}" for i, e in enumerate(lst)]
                send_message(CHAT_ID, "[ 📋 ] ตารางงาน:\n" + "\n".join(lines))
            else:
                send_message(CHAT_ID, "📭 ยังไม่มีตารางงาน")
        elif text.startswith('/remove '):
            try:
                idx = int(text.split()[1]) - 1
                lst = load_schedule()
                if 0 <= idx < len(lst):
                    removed = lst.pop(idx)
                    save_schedule(lst)
                    send_message(CHAT_ID, f"🗑️ ลบ: {removed['time']} → {removed['message']}")
                else:
                    send_message(CHAT_ID, "❌ ไม่พบลำดับนั้น")
            except:
                send_message(CHAT_ID, "❌ ใช้รูปแบบ /remove N")
        elif text == '/clear':
            save_schedule([])
            send_message(CHAT_ID, "🧹 ล้างตารางเรียบร้อยแล้ว")
    return 'ok'

# ========= เริ่มต้นเซิร์ฟเวอร์ =========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
