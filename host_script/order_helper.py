import redis
from common.redis_helper import zrem_all

redis_sell_prices = "sell_prices"
redis_buy_prices = "buy_prices"
redis_order_size = "order_size"


def clear_all_orders(r: redis.client.Redis):
    r.delete(redis_sell_prices, redis_buy_prices, redis_order_size)


def add_buy_order(r: redis.client.Redis, buy_order_id, buy_price, buy_order_size):
    if buy_order_id is None or buy_price is None or buy_order_size is None:
        return
    else:
        r.zadd(redis_buy_prices, {
            buy_order_id: buy_price
        })
        r.zadd(redis_order_size, {
            buy_order_id: buy_order_size
        })


def add_sell_order(r: redis.client.Redis, sell_order_id, sell_price, sell_order_size):
    if sell_order_id is None or sell_price is None or sell_order_size is None:
        return
    else:
        r.zadd(redis_sell_prices, {
            sell_order_id: sell_price
        })
        r.zadd(redis_order_size, {
            sell_order_id: sell_order_size
        })


def pop_highest_buy(r: redis.client.Redis):
    highest_buy = r.zrange(redis_buy_prices, 0, 0, desc=True, withscores=True)
    print(highest_buy)
    if len(highest_buy) == 0:
        return (None, None, None)
    else:
        (buy_order_id, buy_price) = highest_buy[0]
        buy_order_size = r.zscore(redis_order_size, buy_order_id)
        successful_remove = zrem_all(r, {
            redis_buy_prices: buy_order_id,
            redis_order_size: buy_order_id
        })
        if successful_remove:
            return (buy_order_id, buy_price, buy_order_size)
        else:
            return (None, None, None)


def pop_lowest_sell(r: redis.client.Redis):
    lowest_sell = r.zrange(redis_sell_prices, 0, 0, desc=False, withscores=True)
    print(lowest_sell)
    if len(lowest_sell) == 0:
        return (None, None, None)
    else:
        (sell_order_id, sell_price) = lowest_sell[0]
        sell_order_size = r.zscore(redis_order_size, sell_order_id)

        successful_remove = zrem_all(r, {
            redis_sell_prices: sell_order_id,
            redis_order_size: sell_order_id
        })
        if successful_remove:
            return (sell_order_id, sell_price, sell_order_size)
        else:
            return (None, None, None)


def get_new_buy_order(r: redis.client.Redis, buy_order_id, buy_price, buy_order_size, size_to_fulfill):
    if buy_order_size - size_to_fulfill >= 0.00001:
        return (buy_order_id, buy_price, buy_order_size - size_to_fulfill)
    else:
        return pop_highest_buy(r)


def get_new_sell_order(r: redis.client.Redis, sell_order_id, sell_price, sell_order_size, size_to_fulfill):
    if sell_order_size - size_to_fulfill >= 0.00001:
        return (sell_order_id, sell_price, sell_order_size - size_to_fulfill)
    else:
        return pop_lowest_sell(r)


def sell_less_than_buy(r):
    highest_buy = r.zrange(redis_buy_prices, 0, 0, desc=True, withscores=True)
    lowest_sell = r.zrange(redis_sell_prices, 0, 0, desc=False, withscores=True)
    if len(highest_buy) == 0 or len(lowest_sell) == 0:
        return False
    else:
        (_, buy_price) = highest_buy[0]
        (_, sell_price) = lowest_sell[0]
        return sell_price <= buy_price