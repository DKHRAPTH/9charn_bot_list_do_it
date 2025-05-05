
import os
import requests
import time
import json
import datetime
from zoneinfo import ZoneInfo  # เพิ่มไว้ด้านบน

# ดึงค่าจาก Environment Variables
TOKEN    = os.environ['TOKEN']
URL      = f'https://api.telegram.org/bot{TOKEN}/'
LAST_UPDATE_ID = 0
SCHEDULE_FILE  = 'schedule.json'
CHAT_ID        = None

def get_updates():
    global LAST_UPDATE_ID
    resp = requests.get(URL + 'getUpdates', params={'offset': LAST_UPDATE_ID + 1})
    data = resp.json()
    if data.get('ok'):
        for update in data['result']:
            LAST_UPDATE_ID = update['update_id']
            handle_message(update['message'])
    return data['result']

def send_message(chat_id, text):
    requests.post(URL + 'sendMessage', data={'chat_id': chat_id, 'text': text})

def load_schedule():
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_schedule(lst):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(lst, f, ensure_ascii=False)

def add_schedule(time_str, message):
    lst = load_schedule()
    lst.append({'time': time_str, 'message': message})
    save_schedule(lst)

def check_and_notify():
    # ใช้เวลาไทย (Asia/Bangkok)
    now = datetime.datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%H:%M')
    
    lst = load_schedule()
    for event in lst:
        if event['time'] == now and CHAT_ID:
            send_message(CHAT_ID, f"🔔 แจ้งเตือน: {event['message']}")

def handle_message(msg):
    global CHAT_ID
    text = msg.get('text','')
    CHAT_ID = msg['chat']['id']

    if text == '/start':
        send_message(CHAT_ID, "👋 สวัสดีครับ! บอทตารางงานพร้อมใช้แล้ว\nใช้ /add HH:MM ข้อความ เช่น 09:00 แก้ไขโค้ดในRobloxStudio  เพิ่มงาน\nใช้ /list ดูรายการงาน\nใช้ /remove N ลบงานลำดับที่ N")
    elif text.startswith('/add '):
        try:
            parts = text[5:].split(' ',1)
            t, m = parts[0], parts[1]
            # ตรวจรูปแบบเวลา
            datetime.datetime.strptime(t, '%H:%M')
            add_schedule(t, m)
            send_message(CHAT_ID, f"✅ เพิ่มงาน: {t} → {m}")
        except Exception:
            send_message(CHAT_ID, "❌ รูปแบบไม่ถูกต้อง\nใช้ /add HH:MM ข้อความ")
    elif text == '/list':
        lst = load_schedule()
        if lst:
            lines = [f"ตารางงานทั้งหมด มีดังนี้\n{i+1}. {e['time']} → {e['message']}" for i,e in enumerate(lst)]
            send_message(CHAT_ID, "\n".join(lines))
        else:
            send_message(CHAT_ID, "📭 ยังไม่มีงานในตาราง")
    elif text.startswith('/remove '):
        try:
            idx = int(text.split()[1]) - 1
            lst = load_schedule()
            if 0 <= idx < len(lst):
                removed = lst.pop(idx)
                save_schedule(lst)
                send_message(CHAT_ID, f"🗑️ ลบงาน: {removed['time']} → {removed['message']}")
            else:
                send_message(CHAT_ID, "❌ ไม่พบงานลำดับนั้น")
        except Exception:
            send_message(CHAT_ID, "❌ รูปแบบไม่ถูกต้อง\nใช้ /remove N")
    # else: ignore อื่น ๆ

print("🤖 Bot started...")
while True:
    updates = get_updates()
    for u in updates:
        LAST_UPDATE_ID = u['update_id']
        if 'message' in u:
            handle_message(u['message'])
    check_and_notify()
    time.sleep(15)
