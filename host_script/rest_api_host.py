import redis
from host_script.order_helper import sell_less_than_buy, \
    add_order, pop_highest_buy_order, pop_lowest_sell_order, get_new_order_if_necessary, order_can_be_fulfilled, \
    get_all_orders
from host_script.order_class import Order
import uuid
usernames = {
    "user1": {
        "password": "password1",
        "cash_amount": 10000,
        "bit_amount": 20000,
    },
    "user2": {
        "password": "password2",
        "cash_amount": 10000,
        "bit_amount": 20000,
    },
}
import flask
from flask import Flask
app = Flask(__name__)

r = redis.StrictRedis(host='localhost', port=6379, db=0)



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

def is_order(data):
    return "op" in data and data["op"] in ("Buy", "Sell")


def execute_order_if_possible(r: redis.client.Redis):
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


@app.route('/process_order', methods=["POST"])
def process_order():
    required_fields = ["op", "price", "size", "username", "password"]
    for field in required_fields:
        if field not in flask.request.values:
            return f"Field {field} is missing", 400
    username = flask.request.values.get("username")
    password = flask.request.values.get("password")
    op = flask.request.values.get("op")
    price = float(flask.request.values.get("price"))
    size = int(float(flask.request.values.get("size")))
    if username not in usernames:
        return f"User {username} does not exists.", 401
    elif usernames[username]["password"] != password:
        return f"Authentication for user {username} fails.", 401
    elif op == "Buy" and usernames[username]["cash_amount"] < size * price:
        return f"Insufficient Cash", 400
    elif op == "Sell" and usernames[username]["bit_amount"] < size:
        return f"Insufficient micro-Bitcoin", 400
    usernames[username]["cash_amount"] = usernames[username]["amount"] - size * price
    gen_uuid = uuid.uuid4().hex
    order_id = "order:" + gen_uuid
    order = Order(order_id=order_id, side=op, size=size, price=price)
    add_order(r, order)
    print(usernames)
    print(f"Ordering {size} at {price} for {username}")
    return "OK", 200


app.run()
