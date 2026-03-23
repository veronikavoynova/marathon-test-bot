from flask import Flask, request
import requests
import datetime
import json
import os

app = Flask(__name__)

# === НАСТРОЙКИ ===
VK_TOKEN = "vk1.a.ТВОЙ_ТОКЕН"  # Твой токен группы VK
CONFIRMATION_TOKEN = os.environ.get("CONFIRMATION_TOKEN")  # Переменная в Railway

# === ДОСТУПЫ ===
users = {
    123456: "marathon_1",  # ID пользователя VK, который может пользоваться ботом
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
        # Аналогично для 15 и 20 минут
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
    # остальные аналогично...
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

# === ЛОГИКА ТРЕНИРОВКИ ===
def get_today_training(user_id, duration):
    if user_id not in users:
        return "У вас нет доступа 🙏"

    marathon = users[user_id]
    today = datetime.datetime.now().strftime("%a")
    days_map = {"Mon": "Пн", "Tue": "Вт", "Wed": "Ср",
                "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс"}
    day = days_map[today]

    exercises = programs[marathon][duration].get(day, [])
    if not exercises:
        return "Сегодня нет тренировки"

    response = f"Сегодня {day} 💪\n\n"
    for ex in exercises:
        link = videos.get(ex, "")
        response += f"🔹 {ex}\n{link}\n\n"
    return response

# === ОБРАБОТЧИК ВСЕХ СОБЫТИЙ ===
@app.route("/", methods=["POST"])
def handle_vk():
    data = request.get_json()

    # Ошибка раньше: было два route — ВК не видел второй
    if data.get("type") == "confirmation":
        print("VK confirmation request received")  # Лог в Railway
        return CONFIRMATION_TOKEN  # Важно: ровно строка, без лишних пробелов

    if data.get("type") == "message_new":
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

# === Запуск на Railway ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)  # host=0.0.0.0 важно для внешнего доступа