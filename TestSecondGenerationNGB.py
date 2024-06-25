import telebot
from telebot import types
from notion_client import Client
from datetime import datetime, timedelta
import re
import threading

API_TOKEN = '7176346709:AAFxmMDPDMIfxrsG9gvgVnD2qG-zv9iKw4I'
NOTION_TOKEN = 'secret_WeXllCXlCivTJLnmfUZo2a2YseXm8hhhpepkFntMouJ'
DATABASE_ID = 'b3f70fc363b64a89a5eab9a86a75e52b'
CALENDAR_DATABASE_ID = '2915b9e1b3034ff9879ebce5808022be'
GOOGLE_MEET_LINK = 'https://meet.google.com/xdr-wzyt-yrx'

bot = telebot.TeleBot(API_TOKEN)
notion = Client(auth=NOTION_TOKEN)

def add_user_to_notion(name, username, cv_url, specialty):
    url = f"https://t.me/{username}" if username else "N/A"
    notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": name
                        }
                    }
                ]
            },
            "Telegram": {
                "url": url
            },
            "CV": {
                "files": [
                    {
                        "name": "CV",
                        "external": {
                            "url": cv_url
                        }
                    }
                ]
            },
            "Specialty": {
                "select": {
                    "name": specialty
                }
            }
        }
    )

def add_event_to_calendar(date, time, username, specialty):
    start_time = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M')
    end_time = start_time + timedelta(minutes=30)
    notion.pages.create(
        parent={"database_id": CALENDAR_DATABASE_ID},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"Interview with {username} ({specialty})"
                        }
                    }
                ]
            },
            "Date": {
                "date": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            },
            "Google Meet": {
                "url": GOOGLE_MEET_LINK
            }
        }
    )

def send_reminder(chat_id, message, delay):
    threading.Timer(delay, bot.send_message, args=[chat_id, message]).start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id

    # Перше вітальне повідомлення
    welcome_text = "Вітаємо! Ми раді, що ви завітали до нашої компанії NewGen!"
    bot.send_message(chat_id, welcome_text)

    # Друге повідомлення з кнопками
    info_text = "Ми компанія, яка займається інноваційними технологіями. Виберіть один з варіантів нижче:"
    markup = types.InlineKeyboardMarkup()
    
    btn1 = types.InlineKeyboardButton("Сайт компанії", url="https://newgen.company/")
    btn2 = types.InlineKeyboardButton("LinkedIn компанії", url="https://www.linkedin.com/company/newgen-ukraine/?viewAsMember=true")
    btn3 = types.InlineKeyboardButton("Почати планування співбесіди", callback_data="plan_interview")
    
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(chat_id, info_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "plan_interview")
def plan_interview(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Введіть своє ім'я та прізвище англійською мовою:")
    bot.register_next_step_handler(call.message, process_name_step)

def process_name_step(message):
    chat_id = message.chat.id
    name = message.text

    # Перевірка на використання латиниці та наявність двох слів
    if re.match(r'^[A-Za-z]+\s[A-Za-z]+$', name):
        # Запис ім'я в Notion та отримання username користувача
        username = message.from_user.username
        bot.send_message(chat_id, "Дякуємо. Тепер надайте своє CV у форматі PDF:")
        bot.register_next_step_handler(message, process_cv_step, name, username)
    else:
        bot.send_message(chat_id, "Будь ласка, введіть ім'я та прізвище англійською мовою, використовуючи лише латинські букви.")
        bot.register_next_step_handler(message, process_name_step)

def process_cv_step(message, name, username):
    chat_id = message.chat.id

    # Перевірка, чи наданий файл є PDF
    if message.document and message.document.mime_type == 'application/pdf':
        cv_url = bot.get_file_url(message.document.file_id)
        bot.send_message(chat_id, "Дякуємо. Тепер виберіть свою спеціальність:", reply_markup=get_specialty_markup())
        bot.register_next_step_handler(message, process_specialty_step, name, username, cv_url)
    else:
        bot.send_message(chat_id, "Будь ласка, надішліть CV у форматі PDF.")
        bot.register_next_step_handler(message, process_cv_step, name, username)

def get_specialty_markup():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Developer', 'PM', 'QA')
    return markup

def process_specialty_step(message, name, username, cv_url):
    chat_id = message.chat.id
    specialty = message.text

    if specialty in ['Developer', 'PM', 'QA']:
        # Запис даних в Notion
        add_user_to_notion(name, username, cv_url, specialty)
        bot.send_message(chat_id, "Виберіть дату для співбесіди:", reply_markup=get_date_markup())
        bot.register_next_step_handler(message, process_date_step, username, specialty)
    else:
        bot.send_message(chat_id, "Будь ласка, виберіть одну з вказаних спеціальностей.")
        bot.register_next_step_handler(message, process_specialty_step, name, username, cv_url)

def get_date_markup():
    markup = types.InlineKeyboardMarkup()
    today = datetime.today()
    dates = []
    for i in range(1, 8):
        day = today + timedelta(days=i)
        if day.weekday() < 5:  # пропустити суботу і неділю
            dates.append(day)
    for date in dates[:2]:
        btn = types.InlineKeyboardButton(date.strftime('%Y-%m-%d'), callback_data=f"date_{date.strftime('%Y-%m-%d')}")
        markup.add(btn)
    btn_more = types.InlineKeyboardButton("Більше", callback_data="more_dates")
    markup.add(btn_more)
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("date_") or call.data == "more_dates")
def process_date_step(call, username=None, specialty=None):
    chat_id = call.message.chat.id
    if call.data == "more_dates":
        bot.send_message(chat_id, "Виберіть дату для співбесіди:", reply_markup=get_more_date_markup())
    else:
        date = call.data.split("_")[1]
        bot.send_message(chat_id, "Виберіть час для співбесіди:", reply_markup=get_time_markup(date))

def get_more_date_markup():
    markup = types.InlineKeyboardMarkup()
    today = datetime.today()
    dates = []
    for i in range(1, 8):
        day = today + timedelta(days=i)
        if day.weekday() < 5:  # пропустити суботу і неділю
            dates.append(day)
    for date in dates[2:]:
        btn = types.InlineKeyboardButton(date.strftime('%Y-%m-%d'), callback_data=f"date_{date.strftime('%Y-%m-%d')}")
        markup.add(btn)
    btn_back = types.InlineKeyboardButton("Назад", callback_data="plan_interview")
    markup.add(btn_back)
    return markup

def get_time_markup(date):
    markup = types.InlineKeyboardMarkup()
    times = ["12:00", "12:30", "13:00", "13:30", "14:00", "15:30", "16:00", "16:30", "17:00"]
    for time in times:
        btn = types.InlineKeyboardButton(time, callback_data=f"time_{date}_{time}")
        markup.add(btn)
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def process_time_step(call):
    chat_id = call.message.chat.id
    _, date, time = call.data.split("_")
    username = call.message.chat.username
    specialty = "Developer"  # This should be passed from previous steps
    add_event_to_calendar(date, time, username, specialty)
    bot.send_message(chat_id, f"Ваша співбесіда запланована на {date} о {time}. Посилання на Google Meet: {GOOGLE_MEET_LINK}")
    
    # Встановлюємо нагадування за 20 хвилин до початку співбесіди
    interview_time = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M')
    reminder_time = interview_time - timedelta(minutes=20)
    delay = (reminder_time - datetime.now()).total_seconds()
    send_reminder(chat_id, f"Нагадування! Ваша співбесіда через 20 хвилин: {GOOGLE_MEET_LINK}", delay)

if __name__ == '__main__':
    bot.polling(none_stop=True)
