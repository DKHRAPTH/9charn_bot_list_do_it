import os
import requests
import time
import json
import datetime
from backports.zoneinfo import ZoneInfo  # สำหรับ Python < 3.9
from flask import Flask
import threading

# ========== Flask สำหรับ uptime หรือ Railway ==========
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running."

def run_web():
    port = int(os.environ.get('PORT', 8080))  # ใช้ PORT จาก Railway
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
# ======================================================

# ========= Telegram Bot Config =========
TOKEN = os.environ['TOKEN']  # ใส่ token เป็น env บน Railway
URL = f'https://api.telegram.org/bot{TOKEN}/'
LAST_UPDATE_ID = 0
SCHEDULE_FILE = 'schedule.json'
CHAT_ID = None

# ========== ฟังก์ชันบอท ==========
def get_updates():
    global LAST_UPDATE_ID
    resp = requests.get(URL + 'getUpdates', params={'offset': LAST_UPDATE_ID + 1})
    data = resp.json()
    if data.get('ok'):
        for update in data['result']:
            if 'message' in update:
                LAST_UPDATE_ID = update['update_id']
                handle_message(update['message'])

def send_message(chat_id, text):
    requests.post(URL + 'sendMessage', data={'chat_id': chat_id, 'text': text})

def load_schedule():
    if not os.path.exists(SCHEDULE_FILE):
        return []
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

def handle_message(msg):
    global CHAT_ID
    text = msg.get('text', '')
    CHAT_ID = msg['chat']['id']

    if text == '/start':
        send_message(CHAT_ID, "        [ 🤖 ] 9CharnBot \n 👋 ยินดีต้อนรับ! บอทตารางงานพร้อมใช้งานแล้ว\n\n📝 ใช้คำสั่ง:\n• `/add HH:MM ข้อความ` เพิ่มตารางงาน\n• `/list` แสดงตารางงานทั้งหมด\n• `/remove N` ลบตารางงานลำดับที่ N \n Delay 15 s")
    elif text.startswith('/add '):
        try:
            parts = text[5:].split(' ', 1)
            t, m = parts[0], parts[1]
            datetime.datetime.strptime(t, '%H:%M')
            add_schedule(t, m)
            send_message(CHAT_ID, f"✅ เพิ่มงาน: {t} → {m}")
        except:
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : ❌ ใช้รูปแบบ /add HH:MM ข้อความ")
    elif text == '/list':
        lst = load_schedule()
        if lst:
            lines = [f"{i+1}. {e['time']} → {e['message']}" for i, e in enumerate(lst)]
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : 📋 ตารางงาน มีดังนี้ \n" + "\n".join(lines))
        else:
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : 📭 ยังไม่มีตารางงาน")
    elif text.startswith('/remove '):
        try:
            idx = int(text.split()[1]) - 1
            lst = load_schedule()
            if 0 <= idx < len(lst):
                removed = lst.pop(idx)
                save_schedule(lst)
                send_message(CHAT_ID, f"🗑️ ลบ: {removed['time']} → {removed['message']}")
            else:
                send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : ❌ ไม่พบลำดับนั้น")
        except:
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : ❌ ใช้รูปแบบ /remove N")

# ========== Loop หลัก ==========
print("🤖 Bot started...")
while True:
    try:
        get_updates()
        check_and_notify()
        time.sleep(15)
    except Exception as e:
        print("❌ Error:", e)
        time.sleep(5)
