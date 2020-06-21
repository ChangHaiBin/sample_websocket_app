import requests
local_url = "http://127.0.0.1:5000/process_order"
username = "user1"
password = "password1"

while True:
    print("==============================")
    print("Input your command: ")
    command = input()
    if command in ("Buy", "Sell"):
        print("Input price:")
        price = float(input())
        print("Input size:")
        size = float(input())
        dictionary = {
            "username": username,
            "password": password,
            "op": command,
            "price": price,
            "size": size
        }
        result = requests.post(local_url, dictionary)
        print(result.text)
    else:
        print(f"Unknown command {command}")
