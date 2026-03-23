from flask import Flask, request, make_response
import requests
import datetime
import json
import os

app = Flask(__name__)

# === НАСТРОЙКИ ===
VK_TOKEN = os.environ.get("VK_TOKEN")
CONFIRMATION_TOKEN = os.environ.get("CONFIRMATION_TOKEN")

# === ПОЛЬЗОВАТЕЛИ ===
users = {
    37137530: "marathon_1",
}

# === ПРОГРАММЫ ===
programs = {
    "marathon_1": {
        "10": {
            "Пн": ["СПИНА 3", "ПРЕСС 1"],
            "Вт": ["КОЛЕНИ", "НОГИ"],
            "Ср": ["МОЩЬ", "ОСАНКА"],
            "Чт": ["СКАКАЛКА", "СТУЛ"],
            "Пт": ["ПЛАНКИ 4", "РУКИ 2"],
            "Сб": ["БЁДРА", "ЯГОДИЦЫ 2"],
        },
        "15": {
            "Пн": ["СПИНА 3", "ПРЕСС 1", "РОГАТКА"],
            "Вт": ["КОЛЕНИ", "НОГИ", "ЯГОДИЦЫ 2"],
            "Ср": ["РУКИ 2", "МОЩЬ", "ОСАНКА"],
            "Чт": ["СКАКАЛКА", "СТУЛ", "БЁДРА"],
            "Пт": ["ПЛАНКИ 4", "РУКИ 2", "СПИНА 3"],
            "Сб": ["ЯГОДИЦЫ 2", "БЁДРА", "НОГИ"],
        },
        "20": {
            "Пн": ["СПИНА 3", "ПРЕСС 1", "РОГАТКА", "РУКИ 2"],
            "Вт": ["КОЛЕНИ", "НОГИ", "ЯГОДИЦЫ 2", "СТУЛ"],
            "Ср": ["ПЛАНКИ 4", "РУКИ 2", "МОЩЬ", "ОСАНКА"],
            "Чт": ["СКАКАЛКА", "СТУЛ", "БЁДРА", "НОГИ"],
            "Пт": ["РОГАТКА", "ПРЕСС 1", "МОЩЬ", "СПИНА 3"],
            "Сб": ["КОЛЕНИ", "СТУЛ", "СКАКАЛКА", "БЁДРА"],
        }
    }
}

# === ВИДЕО ===
videos = {ex: "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1"
          for ex in ["СПИНА 3", "ПРЕСС 1", "КОЛЕНИ", "НОГИ", "МОЩЬ", "ОСАНКА",
                     "СКАКАЛКА", "СТУЛ", "ПЛАНКИ 4", "РУКИ 2", "БЁДРА", "ЯГОДИЦЫ 2", "РОГАТКА"]}

DAYS_ORDER = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
DAYS_MAP = {"Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс"}


# === КЛАВИАТУРЫ ===

def get_main_keyboard():
    """Главная клавиатура — выбор тренировки на сегодня или расписание."""
    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {"action": {"type": "text", "label": "10 мин"}},
                {"action": {"type": "text", "label": "15 мин"}},
                {"action": {"type": "text", "label": "20 мин"}},
            ],
            [
                {"action": {"type": "text", "label": "📅 Расписание на неделю"}},
            ]
        ]
    }
    return json.dumps(keyboard, ensure_ascii=False)

def get_schedule_keyboard():
    """Клавиатура выбора программы для расписания."""
    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {"action": {"type": "text", "label": "📅 10 мин"}},
                {"action": {"type": "text", "label": "📅 15 мин"}},
                {"action": {"type": "text", "label": "📅 20 мин"}},
            ],
            [
                {"action": {"type": "text", "label": "← Назад"}},
            ]
        ]
    }
    return json.dumps(keyboard, ensure_ascii=False)


# === ОТПРАВКА СООБЩЕНИЯ ===
def send_message(user_id, text, keyboard=None):
    params = {
        "user_id": user_id,
        "message": text,
        "random_id": 0,
        "access_token": VK_TOKEN,
        "v": "5.131",
    }
    if keyboard:
        params["keyboard"] = keyboard
    response = requests.post("https://api.vk.com/method/messages.send", params=params)
    print("VK response:", response.json())


# === ТРЕНИРОВКА НА СЕГОДНЯ ===
def get_today_training(user_id, duration):
    if user_id not in users:
        return "У вас нет доступа 🙏"
    marathon = users[user_id]

    day = DAYS_MAP.get(datetime.datetime.now().strftime("%a"))

    if day == "Вс":
        return "😴 Воскресенье — день отдыха. Восстанавливайся!"

    exercises = programs.get(marathon, {}).get(duration, {}).get(day, [])
    if not exercises:
        return "Сегодня нет тренировки"

    response = f"Сегодня {day} 💪\nПрограмма: {duration} минут\n\n"
    for ex in exercises:
        response += f"🔹 {ex}\n{videos.get(ex, 'ссылка не найдена')}\n\n"
    return response


# === РАСПИСАНИЕ НА НЕДЕЛЮ ===
def get_week_schedule(user_id, duration):
    if user_id not in users:
        return "У вас нет доступа 🙏"
    marathon = users[user_id]

    today = DAYS_MAP.get(datetime.datetime.now().strftime("%a"))
    schedule = programs.get(marathon, {}).get(duration, {})

    response = f"📅 Расписание на неделю ({duration} мин)\n\n"
    for day in DAYS_ORDER:
        exercises = schedule.get(day, [])
        marker = " ← сегодня" if day == today else ""
        if exercises:
            response += f"{day}{marker}:\n"
            for ex in exercises:
                response += f"  • {ex}\n"
        else:
            response += f"{day}: нет тренировки\n"
        response += "\n"

    response += "Воскресенье: день отдыха 😴"
    return response


# === ОБРАБОТЧИК СОБЫТИЙ ===
@app.route("/", methods=["POST"])
def main_handler():
    data = request.get_json(silent=True)
    if not data:
        return make_response("ok", 200)

    print("TOKEN:", VK_TOKEN[:10] if VK_TOKEN else "НЕТ ТОКЕНА")
    print("Received:", data)

    if data.get("type") == "confirmation":
        return make_response(CONFIRMATION_TOKEN, 200)

    if data.get("type") == "message_new":
        obj = data["object"]["message"]
        user_id = obj["from_id"]
        text = obj["text"].strip()

        # Приветствие
        if text.lower() in ["начать", "start"]:
            send_message(user_id,
                "Привет! 👋 Выбери длительность тренировки на сегодня "
                "или посмотри расписание на всю неделю 👇",
                get_main_keyboard())

        # Тренировка на сегодня
        elif text in ["10 мин", "15 мин", "20 мин"]:
            duration = text.replace(" мин", "")
            reply = get_today_training(user_id, duration)
            send_message(user_id, reply, get_main_keyboard())

        # Переход к расписанию — меняем клавиатуру
        elif text == "📅 Расписание на неделю":
            send_message(user_id,
                "Выбери программу для расписания 👇",
                get_schedule_keyboard())

        # Расписание на неделю по программе
        elif text in ["📅 10 мин", "📅 15 мин", "📅 20 мин"]:
            duration = text.replace("📅 ", "").replace(" мин", "")
            reply = get_week_schedule(user_id, duration)
            send_message(user_id, reply, get_main_keyboard())

        # Назад — возвращаем главную клавиатуру
        elif text == "← Назад":
            send_message(user_id,
                "Выбери тренировку на сегодня 👇",
                get_main_keyboard())

        else:
            send_message(user_id,
                "Выбери тренировку на сегодня 👇",
                get_main_keyboard())

    return make_response("ok", 200)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)