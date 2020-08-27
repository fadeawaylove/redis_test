"""
大量的key在同一时间失效
"""
import time
import redis

client = redis.StrictRedis()
key_list = ["key_%s" % i for i in range(100)]


def query():
    for key in key_list:
        ret = client.get(key)
        if not ret:
            print("从数据库获取！")


def init_data():
    for key in key_list:
        client.set(key, "雪崩", ex=10)


if __name__ == '__main__':
    init_data()
    query()
    time.sleep(11)
    query()
