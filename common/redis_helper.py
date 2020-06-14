import redis

def zpop(r: redis.client.Redis, name, desc):
    try:
        r.watch(name)
        zrange_result = r.zrange(name, 0, 0, desc=desc)
        if len(zrange_result) == 0:
            return (None, False)
        result = zrange_result[0]
        p = r.pipeline()
        p.watch(name)
        p.multi()
        p.zrem(name, result)
        p.execute()
        return (result, True)
    except redis.WatchError as e:
        print(e)
        return (None, False)


def zpopmax(r: redis.client.Redis, name):
    return zpop(r, name, desc=True)


def zpopmin(r: redis.client.Redis, name):
    return zpop(r, name, desc=False)


def zrem_all(r: redis.client.Redis, ddict):
    try:
        p = r.pipeline()
        p.watch(*list(ddict.keys()))
        p.multi()
        for (topic, name) in ddict.items():
            p.zrem(topic,name)
        p.execute()
        return True
    except redis.WatchError as e:
        print(e)
        return False