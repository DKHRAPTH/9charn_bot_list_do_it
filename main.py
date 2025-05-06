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

# ========== Config ==========
TOKEN = os.environ['TOKEN']
URL = f'https://api.telegram.org/bot{TOKEN}/'
LAST_UPDATE_ID = 0
SCHEDULE_FILE = 'schedule.json'
START_TIME = time.time()
MAX_RUNTIME_MIN = 29400
DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# ========== Utilities ==========

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
            LAST_UPDATE_ID = update['update_id']
            if 'message' in update:
                handle_message(update['message'])
            elif 'callback_query' in update:
                handle_callback(update['callback_query'])

def send_message(chat_id, text):
    requests.post(URL + 'sendMessage', data={'chat_id': chat_id, 'text': text})

def send_message_with_buttons(chat_id, text, buttons):
    reply_markup = {"inline_keyboard": buttons}
    data = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': json.dumps(reply_markup),
        'parse_mode': 'Markdown'
    }
    requests.post(URL + 'sendMessage', data=data)

def handle_callback(callback):
    query_id = callback['id']
    chat_id = callback['message']['chat']['id']
    data = callback['data']

    command_map = {
        "cmd_add": "➕ /add <วัน> <เวลา> ข้อความ\nตัวอย่าง: /add Mon 19:00 ประชุม",
        "cmd_list": "📋 /list → แสดงรายการงานทั้งหมด",
        "cmd_remove": "❌ /remove N → ลบงานลำดับ N",
        "cmd_clear": "🧹 /clear → ล้างรายการทั้งหมด",
        "cmd_status": "⏱️ /status_list → ตรวจสอบสถานะแจ้งเตือน"
    }

    reply_text = command_map.get(data, "ไม่รู้จักคำสั่งนี้")
    send_message(chat_id, reply_text)
    requests.post(URL + 'answerCallbackQuery', data={'callback_query_id': query_id})

# ========== Schedule Functions ==========

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

def add_schedule(chat_id, time_str, message):
    lst = load_schedule()
    lst.append({'chat_id': chat_id, 'time': time_str, 'message': message, 'notified': False})
    save_schedule(lst)

def check_and_notify():
    now = datetime.datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%Y-%m-%d %H:%M')
    lst = load_schedule()
    updated = False
    for event in lst:
        if event['time'] == now and not event.get('notified', False):
            send_message(event['chat_id'], f"[ 🤖 ] 9CharnBot \n🔔 แจ้งเตือน: {event['message']}")
            event['notified'] = True
            updated = True
    if updated:
        save_schedule(lst)

# ========== Message Handler ==========

def handle_message(msg):
    text = msg.get('text', '')
    chat_id = msg['chat']['id']

    if text == '/start':
        send_message(chat_id,
            "[ 🤖 ] 9CharnBot is Running.... \n"
            "👋 ยินดีต้อนรับสู่ 9CharnBot!\n"
            "พิมพ์ /help เพื่อดูวิธีใช้งานคำสั่งต่าง ๆ\n\n"
            f"vr. {version}"
        )

    elif text == '/help':
        buttons = [
            [{"text": "➕ /add", "callback_data": "cmd_add"},
             {"text": "📋 /list", "callback_data": "cmd_list"}],
            [{"text": "❌ /remove", "callback_data": "cmd_remove"},
             {"text": "🧹 /clear", "callback_data": "cmd_clear"}],
            [{"text": "⏱️ /status_list", "callback_data": "cmd_status"}]
        ]
        send_message_with_buttons(chat_id,
            "[ 🤖 ] 9CharnBot \n"
            "กรุณาเลือกคำสั่งที่ต้องการใช้งาน:", buttons)

    elif text.startswith('/add '):
        try:
            parts = text[5:].split(' ', 2)
            day_str, time_str, message = parts[0], parts[1], parts[2]
            if day_str not in DAYS_OF_WEEK:
                raise ValueError("Invalid day")

            current_date = datetime.datetime.now()
            day_num = DAYS_OF_WEEK.index(day_str)
            days_to_add = (day_num - current_date.weekday()) % 7
            next_date = current_date + datetime.timedelta(days=days_to_add)
            next_day_str = next_date.strftime('%Y-%m-%d')
            datetime.datetime.strptime(time_str, '%H:%M')

            add_schedule(chat_id, f"{next_day_str} {time_str}", message)
            send_message(chat_id, f"[ 🤖 ] 9CharnBot \n✅ เพิ่มงาน: {next_day_str} {time_str} → {message}")
        except Exception as e:
            send_message(chat_id, f"[ 🤖 ] 9CharnBot : ❌ รูปแบบผิด /add <วัน> <เวลา> ข้อความ\nตัวอย่าง: /add Mon 19:00 ประชุม\nข้อผิดพลาด: {str(e)}")

    elif text == '/list':
        lst = [e for e in load_schedule() if e['chat_id'] == chat_id]
        if lst:
            lines = [f"{i+1}. {e['time']} → {e['message']}" for i, e in enumerate(lst)]
            send_message(chat_id, "[ 🤖 ] 9CharnBot \n📋 ตารางงานของคุณ:\n" + "\n".join(lines))
        else:
            send_message(chat_id, "[ 🤖 ] 9CharnBot : 📭 ยังไม่มีตารางงานของคุณ")

    elif text == '/status_list':
        lst = [e for e in load_schedule() if e['chat_id'] == chat_id]
        if lst:
            lines = [f"{i+1}. {e['time']} → {e['message']} ✅" if e.get('notified') else f"{i+1}. {e['time']} → {e['message']} ⏳" for i, e in enumerate(lst)]
            send_message(chat_id, "[ 🤖 ] 9CharnBot \n⏱️ สถานะแจ้งเตือนของคุณ:\n" + "\n".join(lines))
        else:
            send_message(chat_id, "[ 🤖 ] 9CharnBot : 📭 ยังไม่มีตารางงานของคุณ")

    elif text.startswith('/remove '):
        try:
            idx = int(text.split()[1]) - 1
            lst = load_schedule()
            user_events = [e for e in lst if e['chat_id'] == chat_id]
            if 0 <= idx < len(user_events):
                removed = user_events[idx]
                lst.remove(removed)
                save_schedule(lst)
                send_message(chat_id, f"[ 🤖 ] 9CharnBot \n🗑️ ลบ: {removed['time']} → {removed['message']}")
            else:
                send_message(chat_id, "[ 🤖 ] 9CharnBot : ❌ ไม่พบลำดับนั้น")
        except:
            send_message(chat_id, "[ 🤖 ] 9CharnBot : ❌ ใช้รูปแบบ /remove N")

    elif text == '/clear':
        lst = [e for e in load_schedule() if e['chat_id'] != chat_id]
        save_schedule(lst)
        send_message(chat_id, "[ 🤖 ] 9CharnBot : 🧹 ล้างตารางงานของคุณเรียบร้อยแล้ว")

# ========== Main Loop ==========

version = get_bot_version()
print(f"🤖 9CharnBot started with version: {version}")
while True:
    try:
        get_updates()
        check_and_notify()

        lst = load_schedule()
        new_lst = [e for e in lst if not e.get('notified', False)]
        if len(new_lst) != len(lst):
            save_schedule(new_lst)

        if (time.time() - START_TIME) / 60 > MAX_RUNTIME_MIN:
            print("⌛ ปิดบอทเพื่อประหยัด Railway hours")
            exit()

        time.sleep(1)
    except Exception as e:
        print("❌ Error:", e)
        time.sleep(5)
