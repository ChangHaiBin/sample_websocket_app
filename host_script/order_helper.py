import redis
from common.redis_helper import zrem_all
from host_script.order_class import Order
from typing import Tuple

redis_sell_prices_name = "sell_prices"
redis_buy_prices_name = "buy_prices"
redis_order_sizes_name = "order_sizes"


def clear_all_orders(r: redis.client.Redis):
    r.delete(redis_sell_prices_name, redis_buy_prices_name, redis_order_sizes_name)


def add_order(r: redis.client.Redis, order: Order):
    if order.side == "Buy":
        topic_name = redis_buy_prices_name
    else:
        topic_name = redis_sell_prices_name
    r.zadd(topic_name, {
        order.order_id: order.price
    })
    r.zadd(redis_order_sizes_name, {
        order.order_id: order.size
    })


def pop_highest_buy_order(r: redis.client.Redis) -> Tuple[Order, bool]:
    highest_buy = r.zrange(redis_buy_prices_name, 0, 0, desc=True, withscores=True)
    print(highest_buy)
    if len(highest_buy) == 0:
        return (None, False)
    else:
        (buy_order_id, buy_price) = highest_buy[0]
        buy_order_size = r.zscore(redis_order_sizes_name, buy_order_id)
        successful_remove = zrem_all(r, {
            redis_buy_prices_name: buy_order_id,
            redis_order_sizes_name: buy_order_id
        })
        if successful_remove:
            buy_order_id = buy_order_id.decode('utf-8')
            order = Order(buy_order_id, "Buy", buy_order_size, buy_price)
            return (order, True)
        else:
            return (None, False)


def pop_lowest_sell_order(r: redis.client.Redis) -> Tuple[Order, bool]:
    lowest_sell = r.zrange(redis_sell_prices_name, 0, 0, desc=False, withscores=True)
    print(lowest_sell)
    if len(lowest_sell) == 0:
        return (None, False)
    else:
        (sell_order_id, sell_price) = lowest_sell[0]
        sell_order_size = r.zscore(redis_order_sizes_name, sell_order_id)

        successful_remove = zrem_all(r, {
            redis_sell_prices_name: sell_order_id,
            redis_order_sizes_name: sell_order_id
        })
        if successful_remove:
            sell_order_id = sell_order_id.decode('utf-8')
            order = Order(sell_order_id, "Sell", sell_order_size, sell_price)
            return (order, True)
        else:
            return (None, False)


def order_can_be_fulfilled(order: Order, size_to_fulfill: int):
    return order.size - size_to_fulfill <= 0


def get_new_order_if_necessary(r: redis.client.Redis, order: Order, size_to_fulfill) -> Tuple[Order, bool]:
    if order_can_be_fulfilled(order, size_to_fulfill):
        if order.side == "Buy":
            return pop_highest_buy_order(r)
        else:
            return pop_lowest_sell_order(r)
    else:
        new_order = Order(order_id=order.order_id,
                          side=order.side,
                          size=order.size - size_to_fulfill,
                          price=order.price)
        return (new_order, True)


def sell_less_than_buy(r):
    highest_buy = r.zrange(redis_buy_prices_name, 0, 0, desc=True, withscores=True)
    lowest_sell = r.zrange(redis_sell_prices_name, 0, 0, desc=False, withscores=True)
    if len(highest_buy) == 0 or len(lowest_sell) == 0:
        return False
    else:
        (_, buy_price) = highest_buy[0]
        (_, sell_price) = lowest_sell[0]
        return sell_price <= buy_price


def get_all_orders(r: redis.client.Redis):
    # Order sizes and prices are stored in different sorted set
    # May need to investigate if this can handle in high-frequency situation
    order_sizes = dict(r.zrange(redis_order_sizes_name, 0, -1, withscores=True))
    sell_prices = r.zrange(redis_sell_prices_name, 0, -1, withscores=True)
    buy_prices = r.zrange(redis_buy_prices_name, 0, -1, withscores=True)

    orders = [
        Order(order_id=order_id.decode('utf-8'),
              side="Sell",
              size=order_sizes[order_id],
              price=price)
        for order_id, price in sell_prices
    ] + [
        Order(order_id=order_id.decode('utf-8'),
              side="Buy",
              size=order_sizes[order_id],
              price=price)
        for order_id, price in buy_prices
    ]
    return orders
