import yadisk

CLIENT_ID = "742554869fb74aa2b6ab3fc11f39e9d0"
CLIENT_SECRET = "7cedf59181d543559041652acbcea1a9"

y = yadisk.YaDisk(id=CLIENT_ID, secret=CLIENT_SECRET)
url = y.get_code_url()
print("Открой эту ссылку в браузере:", url)

code = input("Вставь код из браузера: ")
response = y.get_token(code)
print("Твой постоянный токен:", response.access_token)