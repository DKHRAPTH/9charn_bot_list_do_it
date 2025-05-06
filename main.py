import os
import requests
import time
import json
import datetime
from flask import Flask
import threading

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running."

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.environ['TOKEN']
URL = f'https://api.telegram.org/bot{TOKEN}/'
LAST_UPDATE_ID = 0
SCHEDULE_FILE = 'schedule.json'
CHAT_ID_FILE = 'chat_id.txt'
START_TIME = time.time()
MAX_RUNTIME_MIN = 29400

def get_updates():
    global LAST_UPDATE_ID, CHAT_ID
    resp = requests.get(URL + 'getUpdates', params={'offset': LAST_UPDATE_ID + 1})
    data = resp.json()
    if data.get('ok'):
        for update in data['result']:
            if 'message' in update:
                LAST_UPDATE_ID = update['update_id']
                CHAT_ID = update['message']['chat']['id']
                save_chat_id(CHAT_ID)
                handle_message(update['message'])

def send_message(chat_id, text):
    data = {'chat_id': chat_id, 'text': text}
    requests.post(URL + 'sendMessage', data=data)

def save_chat_id(chat_id):
    with open(CHAT_ID_FILE, 'w') as f:
        f.write(str(chat_id))

def load_chat_id():
    if os.path.exists(CHAT_ID_FILE):
        with open(CHAT_ID_FILE) as f:
            return int(f.read().strip())
    return None

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
    lst.append({'time': time_str, 'message': message, 'status': 'pending'})
    save_schedule(lst)

def check_and_notify():
    now = datetime.datetime.now(ZoneInfo("Asia/Bangkok"))
    current_time = now.strftime('%H:%M')

    lst = load_schedule()
    changed = False
    for event in lst:
        if event['time'] == current_time and event['status'] == 'pending' and CHAT_ID:
            send_message(CHAT_ID, f"🔔 แจ้งเตือน: {event['message']} ✅ เสร็จแล้ว")
            event['status'] = 'done'
            changed = True
    if changed:
        save_schedule(lst)

def handle_message(msg):
    global CHAT_ID
    text = msg.get('text', '')
    CHAT_ID = msg['chat']['id']
    save_chat_id(CHAT_ID)

    if text == '/start':
        send_message(CHAT_ID, "        [ 🤖 ] 9CharnBot \n 👋 ยินดีต้อนรับ! บอทตารางงานพร้อมใช้งานแล้ว\n\n📝 ใช้คำสั่ง:\n• `/add HH:MM ข้อความ` เพิ่มตารางงาน เช่น `/add 08:00 ไปโรงเรียน`\n• `/list` แสดงตารางงานทั้งหมด\n• `/remove N` ลบตารางงานลำดับที่ N\n• `/clear` ลบตารางงานทั้งหมด\n\nvr.003")
    elif text.startswith('/add '):
        try:
            parts = text[5:].split(' ', 1)
            if len(parts) < 2:
                raise ValueError
            t, m = parts[0], parts[1]
            datetime.datetime.strptime(t, '%H:%M')
            add_schedule(t, m)
            send_message(CHAT_ID, f"✅ เพิ่มงาน: {t} → {m}")
        except:
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : ❌ ใช้รูปแบบ /add HH:MM ข้อความ")
    elif text == '/list':
        lst = load_schedule()
        if lst:
            lines = [f"{i+1}. {e['time']} → {e['message']} ({'✅' if e.get('status') == 'done' else '⏳'})" for i, e in enumerate(lst)]
            send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : 📋 ตารางงานมีดังนี้\n" + "\n".join(lines))
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
        send_message(CHAT_ID, "🧹 ล้างตารางงานทั้งหมดเรียบร้อยแล้ว")

def notify_startup():
    if CHAT_ID:
        send_message(CHAT_ID, "[ 🤖 ] 9CharnBot : บอทเริ่มทำงานแล้ว อัปเดต vr.003)")

print("🤖 Bot started...")

# โหลด chat_id ล่าสุด
CHAT_ID = load_chat_id()

# แจ้งเตือนตอนเริ่มบอท (ถ้ามี chat_id)
notify_startup()

while True:
    try:
        get_updates()
        check_and_notify()
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
