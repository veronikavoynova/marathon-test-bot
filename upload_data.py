import yadisk
import json

YANDEX_TOKEN = "y0__xD7uOWyAhiJrz8gj--A7RYwzNf97weCUEEpn_KrhmZqY0EZm5htFqA34Q"

data = {
    "admins": [37137530],
    "marathons": {
        "марафон_1": {
            "name": "Силовой марафон #1",
            "start_date": "2025-05-01",
            "weeks_base": 4,
            "weeks_vip": 5
        }
    },
    "users": {
        "37137530": {
            "name": "Администратор",
            "marathon": "марафон_1",
            "tariff": "vip"
        }
    },
    "videos": {},
    "schedule": {}
}

with open("data_upload.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

y = yadisk.YaDisk(token=YANDEX_TOKEN)

if not y.exists("/marathon_bot"):
    y.mkdir("/marathon_bot")

y.upload("data_upload.json", "/marathon_bot/data.json", overwrite=True)
print("✅ Файл успешно загружен на Яндекс Диск!")