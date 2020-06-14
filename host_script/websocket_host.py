import asyncio
import json
import websockets
import uuid
import redis
from host_script.order_helper import clear_all_orders, sell_less_than_buy, \
    add_order, pop_highest_buy_order, pop_lowest_sell_order, get_new_order_if_necessary, order_can_be_fulfilled, \
    get_all_orders
from host_script.order_class import Order

#USERS_AND_SUBSCRIBED_TOPIC = {}
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


def is_order(data):
    return "op" in data and data["op"] in ("Buy", "Sell")


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


async def execute_order_if_possible(r: redis.client.Redis):
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


async def record_order(r: redis.client.Redis, order: Order):
    add_order(r, order)
    jjson = assemble_insert_message(order)
    await send_to_all_users_if_possible(json.dumps(jjson))
    await execute_order_if_possible(r)


async def ws_logic(websocket, path):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    await register(websocket, r)
    try:
        async for message in websocket:
            data = json.loads(message)
            if is_order(data):
                side = data["op"]
                price = float(data["price"])
                size = int(data["size"])
                gen_uuid = uuid.uuid4().hex
                order_id = "order:" + gen_uuid
                order = Order(order_id, side, size, price)
                await record_order(r, order)
            else:
                print("unsupported event: {}", data)
    except websockets.exceptions.ConnectionClosedError as e:
        print(e)
    finally:
        await unregister(websocket)

def main():
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    clear_all_orders(r)
    r.close()
    start_server = websockets.serve(ws_logic, "localhost", 6789)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

main()