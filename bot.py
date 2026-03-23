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
          for ex in ["СПИНА 3","ПРЕСС 1","КОЛЕНИ","НОГИ","МОЩЬ","ОСАНКА",
                     "СКАКАЛКА","СТУЛ","ПЛАНКИ 4","РУКИ 2","БЁДРА","ЯГОДИЦЫ 2","РОГАТКА"]}

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
    requests.post("https://api.vk.com/method/messages.send", params=params)

# === ЛОГИКА ТРЕНИРОВОК ===
def get_today_training(user_id, duration):
    if user_id not in users:
        return "У вас нет доступа 🙏"
    marathon = users[user_id]

    today = datetime.datetime.now().strftime("%a")
    days_map = {"Mon":"Пн","Tue":"Вт","Wed":"Ср","Thu":"Чт","Fri":"Пт","Sat":"Сб","Sun":"Вс"}
    day = days_map.get(today)

    if day == "Вс":
        return "😴 Воскресенье — день отдыха. Восстанавливайся!"

    exercises = programs.get(marathon, {}).get(duration, {}).get(day, [])
    if not exercises:
        return "Сегодня нет тренировки"

    response = f"Сегодня {day} 💪\n\n"
    for ex in exercises:
        response += f"🔹 {ex}\n{videos.get(ex, 'ссылка не найдена')}\n\n"
    return response

# === ОБРАБОТЧИК СОБЫТИЙ ===
@app.route("/", methods=["POST"])
def main_handler():
    data = request.get_json(silent=True)
    if not data:
        return make_response("ok", 200)

    print("Received:", data)

    # Подтверждение сервера для ВКонтакте
    if data.get("type") == "confirmation":
        return make_response(CONFIRMATION_TOKEN, 200)

    # Новое сообщение
    if data.get("type") == "message_new":
        obj = data["object"]["message"]
        user_id = obj["from_id"]
        text = obj["text"].strip()

        if text.lower() in ["начать", "start"]:
            send_message(user_id, "Выбери длительность тренировки 👇", get_keyboard())
        elif text in ["10", "15", "20"]:
            reply = get_today_training(user_id, text)
            send_message(user_id, reply)
        else:
            send_message(user_id, "Напиши «начать» чтобы выбрать тренировку 👇")

    return make_response("ok", 200)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)