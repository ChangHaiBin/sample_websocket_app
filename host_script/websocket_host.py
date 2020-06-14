import asyncio
import json
import websockets
import uuid
import redis
from host_script.order_helper import clear_all_orders, add_buy_order, add_sell_order, \
    pop_highest_buy, pop_lowest_sell, get_new_buy_order, get_new_sell_order, sell_less_than_buy

#USERS_AND_SUBSCRIBED_TOPIC = {}
USERS = set()

redis_sell_prices = "sell_prices"
redis_buy_prices = "buy_prices"
redis_order_size = "order_size"

async def register(websocket):
    USERS.add(websocket)
    # jjson = {
    #     "table":"orderBookL2_25",
    #     "keys":["symbol","id","side"],
    #     "types":{"id":"long","price":"float","side":"symbol","size":"long","symbol":"symbol"},
    #     "action": "partial",
    #     "data": [
    #         {"symbol": symbol, "id": gen_uuid, "side": side, "size": size, "price": price}
    #         for (symbol, side, gen_uuid, price, size) in ORDERBOOK_L2
    #     ]
    # }
    # await websocket.send(json.dumps(jjson))
    #await notify_users()


async def send_to_all_users_if_possible(message):
    if len(USERS) != 0:
        await asyncio.wait([user.send(message) for user in USERS])


async def unregister(websocket):
    USERS.remove(websocket)


def is_order(data):
    return "op" in data and data["op"] in ("Buy", "Sell")


async def process_order(symbol, order_side, order_uuid: bytes, order_price, order_size,
                        size_to_fulfill):
    if order_size - size_to_fulfill < 0.00001:
        jjson = {
            "table": "orderBookL2",
            "action": "fulfilled",
            "data": [{"symbol": symbol,
                      "id": order_uuid.decode('utf-8'),
                      "side": order_side}]}
        await send_to_all_users_if_possible(json.dumps(jjson))
    else:
        jjson = {
            "table": "orderBookL2",
            "action": "partial_fulfilled",
            "data": [{"symbol": symbol,
                      "id": order_uuid.decode('utf-8'),
                      "side": order_side,
                      "remaining_size": order_size - size_to_fulfill}]}
        await send_to_all_users_if_possible(json.dumps(jjson))


async def execute_order_if_possible():
    is_sell_less_than_buy = sell_less_than_buy(r)
    if not is_sell_less_than_buy:
        return
    (buy_order_id, buy_price, buy_order_size) = pop_highest_buy(r)
    (sell_order_id, sell_price, sell_order_size) = pop_lowest_sell(r)
    while is_sell_less_than_buy:

        if (buy_price is None) or (sell_price is None) or buy_price < sell_price:
            add_buy_order(r, buy_order_id, buy_price, buy_order_size)
            add_sell_order(r, sell_order_id, sell_price, sell_order_size)
            return

        size_to_fulfill = min(buy_order_size, sell_order_size)
        await process_order("XBTUSD", "Buy", buy_order_id, buy_price, buy_order_size, size_to_fulfill)
        await process_order("XBTUSD", "Sell", sell_order_id, sell_price, sell_order_size, size_to_fulfill)

        (buy_order_id, buy_price, buy_order_size) = \
            get_new_buy_order(r, buy_order_id, buy_price, buy_order_size, size_to_fulfill)
        (sell_order_id, sell_price, sell_order_size) = \
            get_new_sell_order(r, sell_order_id, sell_price, sell_order_size, size_to_fulfill)


def assemble_insert_message(gen_uuid, side, size, price):
    jjson = {
        "table": "orderBookL2",
        "action": "insert",
        "data": [
            {
                "symbol": "XBTUSD",
                "id": gen_uuid,
                "side": side,
                "size": size,
                "price": price
            }
        ]
    }
    return jjson


async def record_order(side, gen_uuid, price, size):
    order_key = "order:" + gen_uuid
    if side == "Buy":
        add_buy_order(r, order_key, price, size)
    elif side == "Sell":
        add_sell_order(r, order_key, price, size)
    else:
        raise Exception("")

    jjson = assemble_insert_message(gen_uuid, side, size, price)
    await send_to_all_users_if_possible(json.dumps(jjson))
    await execute_order_if_possible()


async def ws_logic(websocket, path):
    # register(websocket) sends user_event() to websocket
    await register(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if is_order(data):
                side = data["op"]
                price = float(data["price"])
                size = float(data["size"])
                gen_uuid = uuid.uuid4().hex
                await record_order(side, gen_uuid, price, size)
            else:
                print("unsupported event: {}", data)
    except websockets.exceptions.ConnectionClosedError as e:
        print(e)
    finally:
        await unregister(websocket)


r = redis.StrictRedis(host='localhost', port=6379, db=0)
clear_all_orders(r)
r.close()
start_server = websockets.serve(ws_logic, "localhost", 6789)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()