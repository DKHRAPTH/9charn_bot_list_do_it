import os
import requests
import time
import json
import datetime
from zoneinfo import ZoneInfo
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running."

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web).start()

# ========== Bot config ==========
TOKEN = os.environ['TOKEN']
URL = f'https://api.telegram.org/bot{TOKEN}/'
LAST_UPDATE_ID = 0
SCHEDULE_FILE = 'schedule.json'
CHAT_ID = None
START_TIME = time.time()
MAX_RUNTIME_MIN = 29400  # 490 ชั่วโมง

# ========== Days of the Week ==========
DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# ========== Functions ==========
def get_bot_version():
    try:
        with open('version.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return "unknown"

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
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            data = json.loads(content) if content else []
            for d in data:
                if 'notified' not in d:
                    d['notified'] = False
            return data
    except:
        save_schedule([])
        return []

def save_schedule(lst):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(lst, f, ensure_ascii=False)

def add_schedule(time_str, message):
    lst = load_schedule()
    lst.append({'time': time_str, 'message': message, 'notified': False})
    save_schedule(lst)

def check_and_notify():
    now = datetime.datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%H:%M')  # เวลาในรูปแบบ HH:MM
    lst = load_schedule()
    updated = False
    for event in lst:
        event_time = event['time'].split(' ')[1]  # ตัดแค่เวลาจาก 'YYYY-MM-DD HH:MM'
        if event_time == now and not event.get('notified', False) and CHAT_ID:
            send_message(CHAT_ID, f"🔔 แจ้งเตือน: {event['message']}")
            event['notified'] = True
            updated = True
    if updated:
        save_schedule(lst)

def handle_message(msg):
    global CHAT_ID
    text = msg.get('text', '')
    CHAT_ID = msg['chat']['id']

    if text == '/start':
        send_message(CHAT_ID, "[ 🤖 ] 9CharnBot \n 👋 ยินดีต้อนรับ! บอทตารางงานพร้อมใช้งานแล้ว\n\n📝 ใช้คำสั่ง:\n• `/add <วันในสัปดาห์> <เวลา> ข้อความ` เพิ่มตารางงาน\n• `/list` แสดงตารางงานทั้งหมด\n• `/remove N` ลบตารางงานลำดับที่ N\n• `/clear` ล้างรายการทั้งหมด\n• `/status_list` ตรวจสอบสถานะแจ้งเตือน\n\n Bot Delay 5 s")
    elif text.startswith('/add '):
        try:
            parts = text[5:].split(' ', 2)
            day_str, time_str, message = parts[0], parts[1], parts[2]

            # ตรวจสอบว่าเป็นวันในสัปดาห์ที่ถูกต้อง
            if day_str not in DAYS_OF_WEEK:
                raise ValueError("Invalid day")

            # แปลงวันในสัปดาห์เป็นวันที่จริง
            current_date = datetime.datetime.now()
            day_num = DAYS_OF_WEEK.index(day_str)
            days_to_add = (day_num - current_date.weekday()) % 7
            next_date = current_date + datetime.timedelta(days=days_to_add)
            next_day_str = next_date.strftime('%Y-%m-%d')  # ใช้วันที่ที่คำนวณได้

            # ตรวจสอบรูปแบบเวลา HH:MM
            datetime.datetime.strptime(time_str, '%H:%M')

            # เพิ่มงานในตาราง
            add_schedule(f"{next_day_str} {time_str}", message)
            send_message(CHAT_ID, f"✅ เพิ่มงาน: {next_day_str} {time_str} → {message}")
        except Exception as e:
            send_message(CHAT_ID, f"[ 🤖 ] 9CharnBot : ❌ ใช้รูปแบบ /add <วันในสัปดาห์> <เวลา> ข้อความ\nตัวอย่าง: /add Mon 19:00 ทดสอบ\nข้อผิดพลาด: {str(e)}")
    elif text == '/list':
        lst = load_schedule()
        if lst:
            lines = [f"{i+1}. {e['time']} → {e['message']}" for i, e in enumerate(lst)]
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : 📋 ตารางงาน:\n" + "\n".join(lines))
        else:
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : 📭 ยังไม่มีตารางงาน")
    elif text == '/status_list':
        lst = load_schedule()
        if lst:
            lines = [f"{i+1}. {e['time']} → {e['message']} ✅" if e.get('notified') else f"{i+1}. {e['time']} → {e['message']} ⏳" for i, e in enumerate(lst)]
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : ⏱️ สถานะแจ้งเตือน:\n" + "\n".join(lines))
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
    elif text == '/clear':
        save_schedule([])
        send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : 🧹 ล้างตารางงานทั้งหมดเรียบร้อยแล้ว")

# ========== Main Loop ==========
version = get_bot_version()
print(f"🤖 9CharnBot started with version: {version}")
while True:
    try:
        get_updates()
        check_and_notify()

        # ลบรายการที่แจ้งเตือนแล้ว
        lst = load_schedule()
        new_lst = [e for e in lst if not e.get('notified', False)]
        if len(new_lst) != len(lst):
            save_schedule(new_lst)

        # ตรวจสอบเวลา runtime
        runtime_min = (time.time() - START_TIME) / 60
        if runtime_min > MAX_RUNTIME_MIN:
            if CHAT_ID:
                send_message(CHAT_ID, "[ ⚠️ ] 9CharnBot : ใกล้ถึงขีดจำกัดการใช้งานฟรีของ Railway แล้ว บอทจะปิดตัวเองเพื่อประหยัดเวลา")
            print("⌛ ปิดบอทเพื่อประหยัด Railway hours")
            exit()

        time.sleep(5)
    except Exception as e:
        print("❌ Error:", e)
        time.sleep(5)
