import time
from redis.sentinel import Sentinel

sentinel = Sentinel([("redis-sentinel-1", 26379), ("redis-sentinel-2", 26380), ("redis-sentinel-3", 26381)],
                    socket_timeout=0.1)

# 发现查看下master和slave
master, slave = sentinel.discover_master('mymaster'), sentinel.discover_slaves("mymaster")
print("master: %s, slave: %s" % (master, slave))

# 获取master
m = sentinel.master_for("mymaster", socket_timeout=0.1, password='redis_pwd')
s = sentinel.slave_for("mymaster", socket_timeout=0.1, password="redis_pwd")

m.set("foo", "bar")

r = s.get("foo")
print("foo: %s" % r)

while True:
    print("沉睡中...")
    time.sleep(10)


