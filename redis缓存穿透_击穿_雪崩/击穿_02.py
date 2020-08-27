"""
热点数据缓存失效后，突然来了大量热点数据的请求，这些请求会同时怼到数据库，看起来就像缓存被击穿了
"""
import threading
import time
import redis

client = redis.StrictRedis()

KEY = "hot_data"
LOCK_KEY = "hot_data_lock"


def query_data():
    # 先查询缓存
    ret = client.get(KEY)
    if not ret:
        lock = client.set(LOCK_KEY, "热点数据锁", nx=True, ex=5)
        if lock:
            print("%s 获取到锁" % threading.current_thread().name)
            ret = load_data()
            client.set(KEY, ret, ex=10)
            client.delete(LOCK_KEY)
        else:
            while not ret:
                ret = client.get(KEY)
                if ret:
                    print("%s:从缓存查到数据 %s" % (threading.current_thread().name, ret))
                time.sleep(0.1)
    else:
        print("%s:从缓存查到数据 %s" % (threading.current_thread().name, ret))
    return ret


def load_data():
    # 模拟从数据查询热点数据
    print("%s:从数据库查询热点数据 %s" % (threading.current_thread().name, "我是热点数据"))
    return "我是热点数据"


if __name__ == '__main__':
    tasks = [threading.Thread(target=query_data) for _ in range(100)]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()
