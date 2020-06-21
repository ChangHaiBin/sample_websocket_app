import asyncio
import json
import websockets
import uuid
import redis
from host_script.order_helper import clear_all_orders, sell_less_than_buy, \
    add_order, pop_highest_buy_order, pop_lowest_sell_order, get_new_order_if_necessary, order_can_be_fulfilled, \
    get_all_orders
from host_script.order_class import Order
import pymongo

#USERS_AND_SUBSCRIBED_TOPIC = {}
from host_script.pymongo_helper import add_pymongo_order, reset_database, pymongo_process_order

USERS = set()

redis_sell_prices = "sell_prices"
redis_buy_prices = "buy_prices"
redis_order_size = "order_size"

async def register(websocket, r: redis.client.Redis):
    USERS.add(websocket)
    orders = get_all_orders(r)
    jjson = {
        "table":"orderBookL2",
        "keys":["symbol","id","side"],
        "types":{"id":"long","price":"float","side":"symbol","size":"long","symbol":"symbol"},
        "action": "partial",
        "data": [
            {"symbol": order.symbol,
             "id": order.order_id,
             "side": order.side,
             "size": order.size,
             "price": order.price}
            for order in orders
        ]
    }
    await websocket.send(json.dumps(jjson))


async def send_to_all_users_if_possible(message):
    if len(USERS) != 0:
        await asyncio.wait([user.send(message) for user in USERS])


async def unregister(websocket):
    USERS.remove(websocket)


def is_order(data, pm: pymongo.mongo_client.MongoClient):
    try:
        if data["side"] not in ("Buy", "Sell"):
            return False
        username = data["username"]
        password = data["password"]
        side = data["side"]
        price = float(data["price"])
        size = int(data["size"])
        query = {"username": username, "password": password}
        document = pm["user_accounts"]["accounts"].find_one(query)
        if price <= 0.0 or size <= 0.0:
            return False
        if side == "Buy":
            cash_amount = document["cash_amount"]
            return cash_amount >= price * size
        else: # side == "Sell"
            micro_bitcoin = document["microbitcoin_amount"]
            return micro_bitcoin >= size
    except Exception as e:
        print(e)
        return False


async def process_order(order: Order, size_to_fulfill):
    if order_can_be_fulfilled(order, size_to_fulfill):
        jjson = {
            "table": "orderBookL2",
            "action": "fulfilled",
            "data": [{"symbol": order.symbol,
                      "id": order.order_id,
                      "side": order.side}]}
    else:
        jjson = {
            "table": "orderBookL2",
            "action": "partial_fulfilled",
            "data": [{"symbol": order.symbol,
                      "id": order.order_id,
                      "side": order.side,
                      "remaining_size": order.size - size_to_fulfill}]}
    await send_to_all_users_if_possible(json.dumps(jjson))


async def execute_order_if_possible(r: redis.client.Redis, pm: pymongo.mongo_client.MongoClient):
    is_sell_less_than_buy = sell_less_than_buy(r)
    if not is_sell_less_than_buy:
        return
    (buy_order, buy_pop_successful) = pop_highest_buy_order(r)
    (sell_order, sell_pop_successful) = pop_lowest_sell_order(r)
    while is_sell_less_than_buy:
        if (not buy_pop_successful) or (not sell_pop_successful) or (buy_order.price < sell_order.price):
            if buy_pop_successful:
                add_order(r, buy_order)
            if sell_pop_successful:
                add_order(r, sell_order)
            break

        size_to_fulfill = min(buy_order.size, sell_order.size)
        await process_order(buy_order, size_to_fulfill)
        await process_order(sell_order, size_to_fulfill)
        pymongo_process_order(pm, buy_order, size_to_fulfill)
        pymongo_process_order(pm, sell_order, size_to_fulfill)

        (buy_order, buy_pop_successful) = get_new_order_if_necessary(r, buy_order, size_to_fulfill)
        (sell_order, sell_pop_successful) = get_new_order_if_necessary(r, sell_order, size_to_fulfill)
    # print("Order fulfilled finished")


def assemble_insert_message(order: Order):
    jjson = {
        "table": "orderBookL2",
        "action": "insert",
        "data": [
            {
                "symbol": order.symbol,
                "id": order.order_id,
                "side": order.side,
                "size": order.size,
                "price": order.price
            }
        ]
    }
    return jjson


async def record_order(r: redis.client.Redis, pm: pymongo.mongo_client.MongoClient, order: Order):
    add_order(r, order)
    add_pymongo_order(pm, order)
    jjson = assemble_insert_message(order)
    await send_to_all_users_if_possible(json.dumps(jjson))
    await execute_order_if_possible(r, pm)


async def websocket_logic(websocket, path):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    pm = pymongo.MongoClient("mongodb://localhost:27017/")
    await register(websocket, r)
    try:
        async for message in websocket:
            data = json.loads(message)
            if is_order(data, pm):
                username = data["username"]
                side = data["side"]
                price = float(data["price"])
                size = int(data["size"])
                gen_uuid = uuid.uuid4().hex
                order_id = "order:" + gen_uuid
                order = Order(username, order_id, side, size, price)
                await record_order(r, pm, order)
            else:
                print("Either unsupported event, or data error (e.g. insufficient cash to buy)")
    except websockets.exceptions.ConnectionClosedError as e:
        print(e)
    finally:
        await unregister(websocket)

def main():
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    clear_all_orders(r)
    r.close()
    pm = pymongo.MongoClient("mongodb://localhost:27017/")
    reset_database(pm)
    pm.close()
    start_server = websockets.serve(websocket_logic, "localhost", 6789)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

main()