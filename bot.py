from flask import Flask, request, make_response
import requests
import datetime
import json
import os
import yadisk

app = Flask(__name__)

# === НАСТРОЙКИ ===
VK_TOKEN = os.environ.get("VK_TOKEN")
CONFIRMATION_TOKEN = os.environ.get("CONFIRMATION_TOKEN")
YANDEX_TOKEN = os.environ.get("YANDEX_TOKEN")
DISK_PATH = "/marathon_bot/data.json"  # путь к файлу на Яндекс Диске
LOCAL_PATH = "/tmp/data.json"          # временный файл на сервере

DAYS_ORDER = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
DAYS_MAP = {"Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт", "Fri": "Пт", "Sat": "Сб", "Sun": "Вс"}

# Состояния диалога для каждого админа
# Например: {123456: {"step": "waiting_name", "data": {...}}}
admin_states = {}


# === РАБОТА С ЯНДЕКС ДИСКОМ ===

def get_disk():
    return yadisk.YaDisk(token=YANDEX_TOKEN)

def load_data():
    """Скачивает data.json с Яндекс Диска и читает его."""
    try:
        y = get_disk()
        y.download(DISK_PATH, LOCAL_PATH)
        with open(LOCAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return {"admins": [], "marathons": {}, "users": {}, "videos": {}, "schedule": {}}

def save_data(data):
    """Сохраняет data.json на Яндекс Диск."""
    try:
        with open(LOCAL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        y = get_disk()
        # overwrite=True — перезаписывает файл если он уже есть
        y.upload(LOCAL_PATH, DISK_PATH, overwrite=True)
        print("Данные сохранены на Яндекс Диск")
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")

def init_disk():
    """Создаёт папку на Яндекс Диске если её нет."""
    try:
        y = get_disk()
        if not y.exists("/marathon_bot"):
            y.mkdir("/marathon_bot")
            print("Папка /marathon_bot создана на Яндекс Диске")
        if not y.exists(DISK_PATH):
            # Создаём пустой data.json если его нет
            empty = {
                "admins": [],
                "marathons": {},
                "users": {},
                "videos": {},
                "schedule": {}
            }
            with open(LOCAL_PATH, "w", encoding="utf-8") as f:
                json.dump(empty, f, ensure_ascii=False, indent=2)
            y.upload(LOCAL_PATH, DISK_PATH)
            print("Создан пустой data.json на Яндекс Диске")
    except Exception as e:
        print(f"Ошибка инициализации диска: {e}")


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def is_admin(user_id):
    data = load_data()
    return user_id in data.get("admins", [])

def get_current_week(marathon_id):
    data = load_data()
    marathon = data.get("marathons", {}).get(marathon_id)
    if not marathon:
        return 1
    start = datetime.date.fromisoformat(marathon["start_date"])
    delta = (datetime.date.today() - start).days
    if delta < 0:
        return 1
    week = delta // 7 + 1
    return min(week, marathon.get("weeks_base", 4))


# === КЛАВИАТУРЫ ===

def get_main_keyboard():
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

def get_admin_keyboard():
    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {"action": {"type": "text", "label": "👥 Участники"}},
                {"action": {"type": "text", "label": "🏃 Марафоны"}},
            ],
            [
                {"action": {"type": "text", "label": "🎥 Видео"}},
                {"action": {"type": "text", "label": "👤 Администраторы"}},
            ],
            [
                {"action": {"type": "text", "label": "🏠 Главная"}},
            ]
        ]
    }
    return json.dumps(keyboard, ensure_ascii=False)

def get_users_keyboard():
    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {"action": {"type": "text", "label": "➕ Добавить участника"}},
                {"action": {"type": "text", "label": "➖ Удалить участника"}},
            ],
            [
                {"action": {"type": "text", "label": "📋 Список участников"}},
                {"action": {"type": "text", "label": "📥 Загрузить список"}},
            ],
            [
                {"action": {"type": "text", "label": "◀ Админ меню"}},
            ]
        ]
    }
    return json.dumps(keyboard, ensure_ascii=False)

def get_cancel_keyboard():
    keyboard = {
        "one_time": False,
        "buttons": [
            [{"action": {"type": "text", "label": "❌ Отмена"}}]
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
    data = load_data()
    print(f"Ищем пользователя: '{str(user_id)}'")
    print(f"Все пользователи в файле: {list(data.get('users', {}).keys())}")
    user = data.get("users", {}).get(str(user_id))
    if not user:
        return "У вас нет доступа 🙏"

    marathon_id = user["marathon"]
    week = get_current_week(marathon_id)
    day = DAYS_MAP.get(datetime.datetime.now().strftime("%a"))

    if day == "Вс":
        return "😴 Воскресенье — день отдыха. Восстанавливайся!"

    exercises = data.get("schedule", {}).get(marathon_id, {}).get(duration, {}).get(day, [])
    if not exercises:
        return "Сегодня нет тренировки"

    week_videos = data.get("videos", {}).get(marathon_id, {}).get(str(week), {})

    lines = [f"🔥 Неделя {week}, {day} | {duration} мин\n"]
    warmup = week_videos.get("разминка", "ссылка не найдена")
    lines.append(f"🟡 Разминка:\n{warmup}\n")
    lines.append("💪 Тренировка:")
    for ex in exercises:
        url = week_videos.get(ex, "ссылка не найдена")
        lines.append(f"🔹 {ex}\n{url}")
    cooldown = week_videos.get("заминка", "ссылка не найдена")
    lines.append(f"\n🟣 Заминка:\n{cooldown}")

    return "\n".join(lines)


# === РАСПИСАНИЕ НА НЕДЕЛЮ ===

def get_week_schedule(user_id, duration):
    data = load_data()
    user = data.get("users", {}).get(str(user_id))
    print(f"User lookup: {user_id} -> {user}")
    print(f"All users: {list(data.get('users', {}).keys())}")
    if not user:
        return "У вас нет доступа 🙏"

    marathon_id = user["marathon"]
    week = get_current_week(marathon_id)
    today = DAYS_MAP.get(datetime.datetime.now().strftime("%a"))
    schedule = data.get("schedule", {}).get(marathon_id, {}).get(duration, {})

    lines = [f"📅 Неделя {week} | {duration} мин\n"]
    for day in DAYS_ORDER:
        exercises = schedule.get(day, [])
        marker = " ← сегодня" if day == today else ""
        if exercises:
            lines.append(f"{day}{marker}:")
            for ex in exercises:
                lines.append(f"  • {ex}")
        else:
            lines.append(f"{day}: нет тренировки")
        lines.append("")
    lines.append("Воскресенье: день отдыха 😴")
    return "\n".join(lines)


# === ОБРАБОТКА ЗАГРУЗКИ СПИСКОМ ===

def process_bulk_users(text, admin_id):
    """
    Формат:
    #участники марафон_1 base
    123456789 Маша
    987654321 Оля
    """
    lines = text.strip().split("\n")
    header = lines[0].strip().split()
    if len(header) < 3:
        return "❌ Неверный формат заголовка. Пример:\n#участники марафон_1 base"

    marathon = header[1]
    tariff = header[2]
    data = load_data()
    count = 0

    for line in lines[1:]:
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            vk_id, name = parts
            data["users"][vk_id] = {"name": name, "marathon": marathon, "tariff": tariff}
            count += 1

    save_data(data)
    return f"✅ Добавлено участников: {count}\nМарафон: {marathon}, тариф: {tariff}"

def process_bulk_videos(text):
    """
    Формат:
    #видео марафон_1 1
    разминка https://vk.com/video...
    СПИНА3 https://vk.com/video...
    заминка https://vk.com/video...
    """
    lines = text.strip().split("\n")
    header = lines[0].strip().split()
    if len(header) < 3:
        return "❌ Неверный формат заголовка. Пример:\n#видео марафон_1 1"

    marathon = header[1]
    week = header[2]
    data = load_data()

    if marathon not in data["videos"]:
        data["videos"][marathon] = {}
    if week not in data["videos"][marathon]:
        data["videos"][marathon][week] = {}

    count = 0
    for line in lines[1:]:
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            name, url = parts
            data["videos"][marathon][week][name] = url
            count += 1

    save_data(data)
    return f"✅ Добавлено видео: {count}\nМарафон: {marathon}, неделя: {week}"

def process_bulk_marathons(text):
    """
    Формат:
    #марафоны
    марафон_1 Силовой 2025-05-01 4 5
    марафон_2 Летний 2025-06-01 4 4
    """
    lines = text.strip().split("\n")
    data = load_data()
    count = 0

    for line in lines[1:]:
        parts = line.strip().split(maxsplit=4)
        if len(parts) == 5:
            mid, name, start, weeks_base, weeks_vip = parts
            data["marathons"][mid] = {
                "name": name,
                "start_date": start,
                "weeks_base": int(weeks_base),
                "weeks_vip": int(weeks_vip)
            }
            count += 1

    save_data(data)
    return f"✅ Добавлено марафонов: {count}"


# === ОБРАБОТКА АДМИН ДИАЛОГОВ ===

def handle_admin_dialog(user_id, text):
    """Многошаговые диалоги для админа."""
    state = admin_states.get(user_id, {})
    step = state.get("step")

    # Отмена в любой момент
    if text == "❌ Отмена":
        admin_states.pop(user_id, None)
        send_message(user_id, "Отменено 👌", get_admin_keyboard())
        return True

    # Главное админ меню
    if text == "◀ Админ меню" or text == "🔧 Админ меню":
        admin_states.pop(user_id, None)
        send_message(user_id, "Панель администратора 👇", get_admin_keyboard())
        return True

    # Главная
    if text == "🏠 Главная":
        admin_states.pop(user_id, None)
        send_message(user_id, "Главное меню 👇", get_main_keyboard())
        return True

    # --- УЧАСТНИКИ ---
    if text == "👥 Участники":
        admin_states.pop(user_id, None)
        send_message(user_id, "Управление участниками 👇", get_users_keyboard())
        return True

    if text == "📋 Список участников":
        data = load_data()
        users = data.get("users", {})
        if not users:
            send_message(user_id, "Участников пока нет", get_users_keyboard())
        else:
            lines = [f"👥 Участников: {len(users)}\n"]
            for uid, u in users.items():
                lines.append(f"• {u['name']} (ID: {uid}) — {u['marathon']}, {u['tariff']}")
            send_message(user_id, "\n".join(lines), get_users_keyboard())
        return True

    if text == "➕ Добавить участника":
        admin_states[user_id] = {"step": "add_user_id"}
        send_message(user_id,
            "Введи VK ID участника\n(число на странице профиля):",
            get_cancel_keyboard())
        return True

    if step == "add_user_id":
        if not text.isdigit():
            send_message(user_id, "❌ ID должен быть числом. Попробуй ещё раз:", get_cancel_keyboard())
            return True
        admin_states[user_id] = {"step": "add_user_name", "vk_id": text}
        send_message(user_id, "Введи имя участника:", get_cancel_keyboard())
        return True

    if step == "add_user_name":
        admin_states[user_id]["name"] = text
        admin_states[user_id]["step"] = "add_user_marathon"
        # Показываем список марафонов кнопками
        data = load_data()
        marathons = list(data.get("marathons", {}).keys())
        if not marathons:
            send_message(user_id, "❌ Нет созданных марафонов. Сначала создай марафон.", get_admin_keyboard())
            admin_states.pop(user_id, None)
            return True
        buttons = [[{"action": {"type": "text", "label": m}}] for m in marathons]
        buttons.append([{"action": {"type": "text", "label": "❌ Отмена"}}])
        keyboard = json.dumps({"one_time": True, "buttons": buttons}, ensure_ascii=False)
        send_message(user_id, "Выбери марафон:", keyboard)
        return True

    if step == "add_user_marathon":
        data = load_data()
        marathons = list(data.get("marathons", {}).keys())
        if text not in marathons:
            send_message(user_id, "❌ Выбери марафон из списка", get_cancel_keyboard())
            return True
        admin_states[user_id]["marathon"] = text
        admin_states[user_id]["step"] = "add_user_tariff"
        keyboard = json.dumps({
            "one_time": True,
            "buttons": [
                [{"action": {"type": "text", "label": "base"}}],
                [{"action": {"type": "text", "label": "vip"}}],
                [{"action": {"type": "text", "label": "❌ Отмена"}}],
            ]
        }, ensure_ascii=False)
        send_message(user_id, "Выбери тариф:", keyboard)
        return True

    if step == "add_user_tariff":
        if text not in ["base", "vip"]:
            send_message(user_id, "❌ Выбери тариф: base или vip", get_cancel_keyboard())
            return True
        s = admin_states[user_id]
        data = load_data()
        data["users"][s["vk_id"]] = {
            "name": s["name"],
            "marathon": s["marathon"],
            "tariff": text
        }
        save_data(data)
        admin_states.pop(user_id, None)
        send_message(user_id,
            f"✅ Участник {s['name']} (ID: {s['vk_id']}) добавлен\n"
            f"Марафон: {s['marathon']}, тариф: {text}",
            get_users_keyboard())
        return True

    if text == "➖ Удалить участника":
        admin_states[user_id] = {"step": "delete_user"}
        send_message(user_id, "Введи VK ID участника которого нужно удалить:", get_cancel_keyboard())
        return True

    if step == "delete_user":
        data = load_data()
        if text in data["users"]:
            name = data["users"][text]["name"]
            del data["users"][text]
            save_data(data)
            send_message(user_id, f"✅ Участник {name} удалён", get_users_keyboard())
        else:
            send_message(user_id, f"❌ Участник с ID {text} не найден", get_users_keyboard())
        admin_states.pop(user_id, None)
        return True

    if text == "📥 Загрузить список":
        admin_states[user_id] = {"step": "bulk_users"}
        send_message(user_id,
            "Отправь список участников в таком формате:\n\n"
            "#участники марафон_1 base\n"
            "123456789 Маша\n"
            "987654321 Оля\n"
            "555000111 Петя",
            get_cancel_keyboard())
        return True

    if step == "bulk_users":
        if text.startswith("#участники"):
            reply = process_bulk_users(text, user_id)
            admin_states.pop(user_id, None)
            send_message(user_id, reply, get_users_keyboard())
        else:
            send_message(user_id, "❌ Начни сообщение с #участники", get_cancel_keyboard())
        return True

    # --- МАРАФОНЫ ---
    if text == "🏃 Марафоны":
        admin_states.pop(user_id, None)
        data = load_data()
        marathons = data.get("marathons", {})
        lines = ["📋 Марафоны:\n"] if marathons else ["Марафонов пока нет\n"]
        for mid, m in marathons.items():
            lines.append(f"• {m['name']} ({mid})\n  Старт: {m['start_date']}, "
                        f"base: {m['weeks_base']} нед, vip: {m['weeks_vip']} нед")
        lines.append("\nЧтобы добавить марафоны — отправь список:\n\n"
                    "#марафоны\n"
                    "марафон_1 Силовой 2025-05-01 4 5\n"
                    "марафон_2 Летний 2025-06-01 4 4")
        admin_states[user_id] = {"step": "bulk_marathons"}
        send_message(user_id, "\n".join(lines), get_cancel_keyboard())
        return True

    if step == "bulk_marathons":
        if text.startswith("#марафоны"):
            reply = process_bulk_marathons(text)
            admin_states.pop(user_id, None)
            send_message(user_id, reply, get_admin_keyboard())
        else:
            send_message(user_id, "❌ Начни сообщение с #марафоны", get_cancel_keyboard())
        return True

    # --- ВИДЕО ---
    if text == "🎥 Видео":
        admin_states[user_id] = {"step": "bulk_videos"}
        send_message(user_id,
            "Отправь список видео в таком формате:\n\n"
            "#видео марафон_1 1\n"
            "разминка https://vk.com/video...\n"
            "СПИНА3 https://vk.com/video...\n"
            "ПРЕСС1 https://vk.com/video...\n"
            "заминка https://vk.com/video...",
            get_cancel_keyboard())
        return True

    if step == "bulk_videos":
        if text.startswith("#видео"):
            reply = process_bulk_videos(text)
            admin_states.pop(user_id, None)
            send_message(user_id, reply, get_admin_keyboard())
        else:
            send_message(user_id, "❌ Начни сообщение с #видео", get_cancel_keyboard())
        return True

    # --- АДМИНИСТРАТОРЫ ---
    if text == "👤 Администраторы":
        admin_states.pop(user_id, None)
        data = load_data()
        admins = data.get("admins", [])
        keyboard = json.dumps({
            "one_time": False,
            "buttons": [
                [{"action": {"type": "text", "label": "➕ Добавить админа"}}],
                [{"action": {"type": "text", "label": "➖ Удалить админа"}}],
                [{"action": {"type": "text", "label": "◀ Админ меню"}}],
            ]
        }, ensure_ascii=False)
        send_message(user_id, f"👤 Администраторов: {len(admins)}\nID: {admins}", keyboard)
        return True

    if text == "➕ Добавить админа":
        admin_states[user_id] = {"step": "add_admin"}
        send_message(user_id, "Введи VK ID нового администратора:", get_cancel_keyboard())
        return True

    if step == "add_admin":
        if not text.isdigit():
            send_message(user_id, "❌ ID должен быть числом", get_cancel_keyboard())
            return True
        new_admin = int(text)
        data = load_data()
        if new_admin not in data["admins"]:
            data["admins"].append(new_admin)
            save_data(data)
            send_message(user_id, f"✅ Пользователь {new_admin} теперь администратор", get_admin_keyboard())
        else:
            send_message(user_id, "Этот пользователь уже администратор", get_admin_keyboard())
        admin_states.pop(user_id, None)
        return True

    if text == "➖ Удалить админа":
        admin_states[user_id] = {"step": "remove_admin"}
        send_message(user_id, "Введи VK ID администратора которого нужно удалить:", get_cancel_keyboard())
        return True

    if step == "remove_admin":
        if not text.isdigit():
            send_message(user_id, "❌ ID должен быть числом", get_cancel_keyboard())
            return True
        rm_admin = int(text)
        data = load_data()
        if rm_admin == user_id:
            send_message(user_id, "❌ Нельзя удалить самого себя", get_admin_keyboard())
        elif rm_admin in data["admins"]:
            data["admins"].remove(rm_admin)
            save_data(data)
            send_message(user_id, f"✅ Пользователь {rm_admin} больше не администратор", get_admin_keyboard())
        else:
            send_message(user_id, "❌ Этот пользователь не администратор", get_admin_keyboard())
        admin_states.pop(user_id, None)
        return True

    return False


# === ОБРАБОТЧИК СОБЫТИЙ ===

@app.route("/", methods=["POST"])
def main_handler():
    data = request.get_json(silent=True)
    if not data:
        return make_response("ok", 200)

    print("Received:", data)

    if data.get("type") == "confirmation":
        return make_response(CONFIRMATION_TOKEN, 200)

    if data.get("type") == "message_new":
        obj = data["object"]["message"]
        user_id = obj["from_id"]
        text = obj["text"].strip()

        # Сначала проверяем — это админ?
        if is_admin(user_id):
            # Кнопка входа в админ меню
            if text == "🔧 Админ меню":
                admin_states.pop(user_id, None)
                send_message(user_id, "Панель администратора 👇", get_admin_keyboard())
                return make_response("ok", 200)
            # Обрабатываем диалог если есть активный шаг, или нажата кнопка меню
            if handle_admin_dialog(user_id, text):
                return make_response("ok", 200)

        # Обычные команды для всех
        if text.lower() in ["начать", "start"]:
            msg = "Привет! 👋 Выбери тренировку на сегодня 👇"
            keyboard = get_main_keyboard()
            # Если это админ — добавляем кнопку входа в панель
            if is_admin(user_id):
                kb = json.loads(get_main_keyboard())
                kb["buttons"].append([{"action": {"type": "text", "label": "🔧 Админ меню"}}])
                keyboard = json.dumps(kb, ensure_ascii=False)
            send_message(user_id, msg, keyboard)

        elif text in ["10 мин", "15 мин", "20 мин"]:
            duration = text.replace(" мин", "")
            reply = get_today_training(user_id, duration)
            send_message(user_id, reply, get_main_keyboard())

        elif text == "📅 Расписание на неделю":
            send_message(user_id, "Выбери программу 👇", get_schedule_keyboard())

        elif text in ["📅 10 мин", "📅 15 мин", "📅 20 мин"]:
            duration = text.replace("📅 ", "").replace(" мин", "")
            reply = get_week_schedule(user_id, duration)
            send_message(user_id, reply, get_main_keyboard())

        elif text == "← Назад":
            send_message(user_id, "Выбери тренировку 👇", get_main_keyboard())

        else:
            send_message(user_id, "Выбери тренировку 👇", get_main_keyboard())

    return make_response("ok", 200)


# === ЗАПУСК ===

init_disk()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)