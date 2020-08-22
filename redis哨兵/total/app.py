import time
import random
import traceback
from redis.sentinel import Sentinel

sentinel = Sentinel([("redis-sentinel-1", 26379), ("redis-sentinel-2", 26379), ("redis-sentinel-3", 26379)],
                    socket_timeout=0.1)


while True:
    try:
        # 发现查看下master和slave
        master, slave = sentinel.discover_master('mymaster'), sentinel.discover_slaves("mymaster")
        print("master: %s, slave: %s" % (master, slave))
        # 获取master
        m = sentinel.master_for("mymaster", socket_timeout=0.1, password='redis_pwd')
        s = sentinel.slave_for("mymaster", socket_timeout=0.1, password="redis_pwd")
        value = random.randint(1, 1000)
        m.set("test_int", value)
        r = s.get("test_int")
        print("set test_int: %s, get test_int: %s" % (value, r))
        print("沉睡中...")
    except:
        print(traceback.format_exc())
    time.sleep(5)



