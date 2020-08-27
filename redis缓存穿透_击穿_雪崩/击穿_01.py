"""
热点数据缓存失效后，突然来了大量热点数据的请求，这些请求会同时怼到数据库，看起来就像缓存被击穿了
"""
import threading
import redis

client = redis.StrictRedis()

KEY = "hot_data"


def query_data():
    ret = client.get(KEY)
    if not ret:
        return load_data()


def load_data():
    # 模拟从数据查询热点数据
    print("从数据库查询热点数据")
    return "我是热点数据"


if __name__ == '__main__':
    tasks = [threading.Thread(target=query_data) for _ in range(10)]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()
