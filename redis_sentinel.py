"""
哨兵使用
"""

from redis.sentinel import Sentinel

sentinel = Sentinel([('localhost', 26379)], socket_timeout=0.1)

master = sentinel.master_for("mymaster", socket_timeout=0.1)

slave = sentinel.slave_for("mymaster", socket_timeout=0.1)

print(master, slave)

master.set("test_master", "我是你爸爸")

print(slave.get("test_master"))
