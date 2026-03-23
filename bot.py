from flask import Flask, request
import requests
import datetime
import json

app = Flask(__name__)

# === НАСТРОЙКИ ===
VK_TOKEN = "ТВОЙ_ТОКЕН"
CONFIRMATION_TOKEN = "ТВОЙ_CONFIRMATION"

# === ДОСТУПЫ ===
users = {
    123456: "marathon_1",
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
            "Сб": ["БЕДРА", "ЯГОДИЦЫ 2"],
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
videos = {
    "СПИНА 3": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "ПРЕСС 1": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "КОЛЕНИ": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "НОГИ": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "МОЩЬ": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "ОСАНКА": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "СКАКАЛКА": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "СТУЛ": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "ПЛАНКИ 4": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "РУКИ 2": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "БЕДРА": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "БЁДРА": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "ЯГОДИЦЫ 2": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
    "РОГАТКА": "https://vkvideo.ru/playlist/-211232966_15/video-211232966_456241213?linked=1",
}

# === КНОПКИ ===
def get_keyboard():
    keyboard = {
        "one_time": True,
        "buttons": [
            [{"action": {"type": "text", "label": "10"}}],
            [{"action": {"type": "text", "label": "15"}}],
            [{"action": {"type": "text", "label": "20"}}]
        ]
    }
    return json.dumps(keyboard)

# === ОТПРАВКА СООБЩЕНИЯ ===
def send_message(user_id, text, keyboard=None):
    requests.post(
        "https://api.vk.com/method/messages.send",
        params={
            "user_id": user_id,
            "message": text,
            "random_id": 0,
            "access_token": VK_TOKEN,
            "v": "5.131",
            "keyboard": keyboard
        }
    )

# === ЛОГИКА ===
def get_today_training(user_id, duration):
    if user_id not in users:
        return "У вас нет доступа 🙏"

    marathon = users[user_id]

    today = datetime.datetime.now().strftime("%a")

    days_map = {
        "Mon": "Пн", "Tue": "Вт", "Wed": "Ср",
        "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс"
    }

    day = days_map[today]

    try:
        exercises = programs[marathon][duration][day]
    except:
        return "Сегодня нет тренировки"

    response = f"Сегодня {day} 💪\n\n"

    for ex in exercises:
        link = videos.get(ex, "")
        response += f"🔹 {ex}\n{link}\n\n"

    return response

# === ОБРАБОТКА СОБЫТИЙ ===
@app.route("/", methods=["POST"])
def main():
    data = request.json

    if data["type"] == "confirmation":
        return CONFIRMATION_TOKEN

    if data["type"] == "message_new":
        user_id = data["object"]["message"]["from_id"]
        text = data["object"]["message"]["text"]

        if text.lower() in ["начать", "start"]:
            send_message(user_id, "Выбери длительность тренировки 👇", get_keyboard())

        elif text in ["10", "15", "20"]:
            reply = get_today_training(user_id, text)
            send_message(user_id, reply)

        else:
            send_message(user_id, "Напиши 'начать'")

    return "ok"

if __name__ == "__main__":
    app.run(port=5000)