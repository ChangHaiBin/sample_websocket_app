import websocket
import threading
import time, json, datetime, threading



class SampleSocket:

    def __init__(self):
        pass

    def connect(self, wsURL):
        '''Connect to the websocket in a thread.'''
        self.ws = websocket.WebSocketApp(wsURL,
                                         on_message=self.__on_message,
                                         on_close=self.__on_close,
                                         on_open=self.__on_open,
                                         on_error=self.__on_error,
                                         header=[])

        self.wst = threading.Thread(target=lambda: self.ws.run_forever())
        self.wst.daemon = True
        self.wst.start()
        print("Started thread")

        # Wait for connect before continuing
        conn_timeout = 5
        while (not self.ws.sock or not self.ws.sock.connected) and conn_timeout:
            time.sleep(1)
            conn_timeout -= 1
        if not conn_timeout:
            self.exit()
            raise websocket.WebSocketTimeoutException('Couldn\'t connect to WS! Exiting.')

    def exit(self):
        '''Call this to exit - will close websocket.'''
        self.exited = True
        try:
            self.ws.close()
        except Exception as e:
            print(e)

    def __on_message(self, message):
        print(message)

    def __on_error(self, error):
        '''Called on fatal websocket errors. We exit on these.'''
        if not self.exited:
            print("Error : %s" % error)
            raise websocket.WebSocketException(error)

    def __on_open(self):
        '''Called when the WS opens.'''
        print("Websocket Opened.")

    def __on_close(self):
        '''Called on websocket close.'''
        print('Websocket Closed')


ss = SampleSocket()
ss.connect("ws://localhost:6789/")

username = "username1"
password = "password1"

import random, time

for i in range(0,1000):
    indicator = random.randint(0, 1)
    if indicator == 1:
        command = "Buy"
        price = 3.10 + 0.01*random.randint(0,6)
        # Buy between 3.10 and 3.16
    else:
        command = "Sell"
        price = 3.14 + 0.01*random.randint(0,6)
        # Sell between 3.14 and 3.2
    size = random.randint(1,10)

    jjson = {"side": command,
             "price": price,
             "size": size,
             "username": username,
             "password": password}
    print("===", jjson)
    ss.ws.send(json.dumps(jjson))

    time.sleep(0.01)


while True:
    print("==============================")
    print("Input your command: ")
    command = input()
    if command in ("Buy", "Sell"):
        print("Input price:")
        price = float(input())
        print("Input size:")
        size = float(input())
        jjson = {"side": command,
                 "price": price,
                 "size": size,
                 "username": username,
                 "password": password}
        ss.ws.send(json.dumps(jjson))
    else:
        print(f"Unknown command {command}")
