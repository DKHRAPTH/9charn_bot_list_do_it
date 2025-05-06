import os
import json
import datetime
from flask import Flask, request
import requests
from zoneinfo import ZoneInfo
from threading import Thread
import time

TOKEN = os.environ.get('BOT_TOKEN')
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'
SCHEDULE_FILE = 'schedule.json'

app = Flask(__name__)

def send_message(chat_id, text):
    url = f'{BASE_URL}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

def load_schedule(chat_id):
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if str(chat_id) not in data:
                data[str(chat_id)] = []
            for d in data[str(chat_id)]:
                if 'notified' not in d:
                    d['notified'] = False
            return data[str(chat_id)]
    except:
        save_schedule(chat_id, [])
        return []

def save_schedule(chat_id, lst):
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    data[str(chat_id)] = lst
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def add_schedule(chat_id, time_str, message):
    lst = load_schedule(chat_id)
    lst.append({'time': time_str, 'message': message, 'notified': False})
    save_schedule(chat_id, lst)

def check_and_notify():
    while True:
        now = datetime.datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%H:%M')
        try:
            with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        except:
            all_data = {}

        updated = False
        for chat_id, events in all_data.items():
            for event in events:
                event_time = event['time'].split(' ')[1]
                if event_time == now and not event.get('notified', False):
                    send_message(chat_id, f"[ 🤖 ] 9CharnBot \n🔔 แจ้งเตือน: {event['message']}")
                    event['notified'] = True
                    updated = True
            all_data[chat_id] = events

        if updated:
            with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False)

        time.sleep(60)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'message' in data:
        handle_message(data['message'])
    return 'ok'

def handle_message(msg):
    text = msg.get('text', '')
    chat_id = str(msg['chat']['id'])

    if text == '/start':
        send_message(chat_id, "[ 🤖 ] 9CharnBot \n👋 ยินดีต้อนรับ! พิมพ์ /help เพื่อดูคำสั่งทั้งหมด")

    elif text == '/help':
        send_message(chat_id, (
            "[ 🤖 ] 9CharnBot : รายการคำสั่ง\n"
            "/add [วัน] [เวลา] [ข้อความ] - เพิ่มงาน เช่น /add พรุ่งนี้ 09:00 ประชุม\n"
            "/list - ดูรายการงาน\n"
            "/remove [ลำดับ] - ลบงานตามลำดับ\n"
            "/clear - ล้างงานทั้งหมด\n"
            "/status_list - ดูสถานะการแจ้งเตือนของแต่ละงาน"
        ))

    elif text.startswith('/add '):
        try:
            parts = text[5:].split(' ', 2)
            day_str, time_str, message = parts[0], parts[1], parts[2]

            now = datetime.datetime.now(ZoneInfo("Asia/Bangkok"))
            if day_str == "พรุ่งนี้":
                next_day = now + datetime.timedelta(days=1)
            elif day_str == "วันนี้":
                next_day = now
            else:
                send_message(chat_id, "[ 🤖 ] 9CharnBot : ❌ ใช้ได้แค่ 'วันนี้' หรือ 'พรุ่งนี้'")
                return

            next_day_str = next_day.strftime('%Y-%m-%d')
            add_schedule(chat_id, f"{next_day_str} {time_str}", message)
            send_message(chat_id, f"[ 🤖 ] 9CharnBot \n✅ เพิ่มงาน: {next_day_str} {time_str} → {message}")
        except:
            send_message(chat_id, "[ 🤖 ] 9CharnBot : ❌ รูปแบบไม่ถูกต้อง /add [วัน] [เวลา] [ข้อความ]")

    elif text == '/list':
        lst = load_schedule(chat_id)
        if not lst:
            send_message(chat_id, "[ 🤖 ] 9CharnBot : ไม่มีงานในตาราง")
        else:
            msg = "[ 🤖 ] 9CharnBot : รายการงาน\n"
            for i, item in enumerate(lst):
                msg += f"{i+1}. {item['time']} → {item['message']}\n"
            send_message(chat_id, msg)

    elif text == '/status_list':
        lst = load_schedule(chat_id)
        if not lst:
            send_message(chat_id, "[ 🤖 ] 9CharnBot : ไม่มีงานในตาราง")
        else:
            msg = "[ 🤖 ] 9CharnBot : สถานะแจ้งเตือน\n"
            for i, item in enumerate(lst):
                status = "แจ้งแล้ว" if item.get('notified', False) else "ยังไม่แจ้ง"
                msg += f"{i+1}. {item['time']} → {item['message']} [{status}]\n"
            send_message(chat_id, msg)

    elif text.startswith('/remove '):
        try:
            idx = int(text.split()[1]) - 1
            lst = load_schedule(chat_id)
            if 0 <= idx < len(lst):
                removed = lst.pop(idx)
                save_schedule(chat_id, lst)
                send_message(chat_id, f"[ 🤖 ] 9CharnBot \n🗑️ ลบ: {removed['time']} → {removed['message']}")
            else:
                send_message(chat_id, "[ 🤖 ] 9CharnBot : ❌ ไม่พบลำดับนั้น")
        except:
            send_message(chat_id, "[ 🤖 ] 9CharnBot : ❌ ใช้รูปแบบ /remove [ลำดับ]")

    elif text == '/clear':
        save_schedule(chat_id, [])
        send_message(chat_id, "[ 🤖 ] 9CharnBot : 🧹 ล้างตารางงานทั้งหมดเรียบร้อยแล้ว")

if __name__ == '__main__':
    Thread(target=check_and_notify, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
