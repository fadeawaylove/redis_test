import time
import json
import redis

client = redis.StrictRedis()

BLOOM_KEY = "all_user"


def get_user_info(uid):
    r = client.getbit(BLOOM_KEY, uid % 1000)
    if r == 0:
        return "用户不存在"
    key = "user_info:%s" % uid
    user_info = client.get(key)
    if not user_info:
        user_info = query_user_info_from_mysql(uid)
        if not user_info:
            client.set(key, "不存在", ex=60)
    else:
        user_info = user_info
    return user_info


def query_user_info_from_mysql(uid):
    # 模拟从数据库查询
    if uid < 0:
        time.sleep(0.1)
        return None
    return {"name": "张三", "age": 18, "uid": uid}


def cache_all_user():
    uids = range(1, 11)
    map_size = 1000
    for u in uids:
        client.set("user_info:%s" % u, json.dumps(query_user_info_from_mysql(u)))
        client.setbit(BLOOM_KEY, u % map_size, 1)  # 模拟布隆过滤器，实际上是使用的多个hash函数


if __name__ == '__main__':
    cache_all_user()
    for i in range(-10, 0):
        info = get_user_info(i)
        print(info)
    print(get_user_info(1))
