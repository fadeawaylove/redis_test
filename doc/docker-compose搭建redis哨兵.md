# Redis哨兵（Sentinel）模式


一般为了可用性，redis会搭建成主从模式，但是当主服务器宕机后，需要手动将从服务器切换为主服务器，这样不进费时费力，还会造成一段时间服务器不可用，所以单独的主从模式并不是很好，可以使用哨兵模式做到自动切换主从服务器。

## 哨兵模式
哨兵模式是一种特殊的模式，首先Redis提供了哨兵的命令，哨兵是一个独立的进程，作为进程，它会独立运行。其原理是哨兵通过发送命令，等待Redis服务器响应，从而监控运行的多个Redis实例。
![https://raw.githubusercontent.com/fadeawaylove/article-images/master/164640d92239dacf%3Fimageslim](https://raw.githubusercontent.com/fadeawaylove/article-images/master/16464072b3430480%3Fimageslim)

故障切换（failover）：主服务器宕机，哨兵1先检测到这个结果，系统并不会马上进行failover过程，仅仅是哨兵1主观的认为主服务器不可用，这个现象成为主观下线。当后面的哨兵也检测到主服务器不可用，并且数量达到一定值时，那么哨兵之间就会进行一次投票，投票的结果由一个哨兵发起，进行failover操作。切换成功后，就会通过发布订阅模式，让各个哨兵把自己监控主机信息更新，这个过程称为客观下线。这样对于客户端而言，一切都是透明的。

![https://raw.githubusercontent.com/fadeawaylove/article-images/master/164640d92239dacf%3Fimageslim](https://raw.githubusercontent.com/fadeawaylove/article-images/master/164640d92239dacf%3Fimageslim)

## 使用docker-compose搭建redis哨兵模式
目录：
```shell
% tree
.
├── app.py
├── docker-compose.yml
└── sentinel.conf
```

`docker-compose.yml`:
```yml
version: '3'
services:
  master:
    image: redis
    container_name: redis-master
    command: redis-server --requirepass redis_pwd --masterauth redis_pwd
    ports:
      - 6380:6379
  slave1:
    image: redis
    container_name: redis-slave-1
    ports:
      - 6381:6379
    command: redis-server --slaveof redis-master 6379 --requirepass redis_pwd --masterauth redis_pwd
  slave2:
    image: redis
    container_name: redis-slave-2
    ports:
      - 6382:6379
    command: redis-server --slaveof redis-master 6379 --requirepass redis_pwd --masterauth redis_pwd
  sentinel1:
    image: redis
    container_name: redis-sentinel-1
    depends_on: 
      - master
      - slave1
      - slave2
    ports:
      - 26379:26379
    volumes:
      - ./sentinel.conf:/usr/local/etc/redis/sentinel.conf
    command: bash -c "cp /usr/local/etc/redis/sentinel.conf /usr/local/etc/redis/sentinel1.conf && redis-sentinel /usr/local/etc/redis/sentinel1.conf"
  sentinel2:
    image: redis
    container_name: redis-sentinel-2
    depends_on: 
      - master
      - slave1
      - slave2
    ports:
      - 26380:26379
    command: bash -c "cp /usr/local/etc/redis/sentinel.conf /usr/local/etc/redis/sentinel2.conf && redis-sentinel /usr/local/etc/redis/sentinel2.conf"
    volumes:
      - ./sentinel.conf:/usr/local/etc/redis/sentinel.conf
  sentinel3:
    image: redis
    container_name: redis-sentinel-3
    depends_on: 
      - master
      - slave1
      - slave2
    ports:
      - 26381:26379
    command: bash -c "cp /usr/local/etc/redis/sentinel.conf /usr/local/etc/redis/sentinel3.conf && redis-sentinel /usr/local/etc/redis/sentinel3.conf"
    volumes:
      - ./sentinel.conf:/usr/local/etc/redis/sentinel.conf
  app:
    container_name: app-test
    image: python:3.6-alpine
    depends_on: 
      - sentinel1
      - sentinel2
      - sentinel3
    volumes:
      - ./app.py:/root/app.py
    command:
      /bin/sh -c "pip3 install redis && python -u /root/app.py"

```

`sentinel.conf`:
```shell
port 26379
dir /tmp
sentinel monitor mymaster redis-master 6379 2
sentinel auth-pass mymaster redis_pwd
sentinel down-after-milliseconds mymaster 1000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 180000
sentinel deny-scripts-reconfig yes

```

`app.py`:
```python
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

```

输入命令`docker-compose up`,查看终端的日志就可以看到输出了：
![https://raw.githubusercontent.com/fadeawaylove/article-images/master/WX20200823-214438%402x.png](https://raw.githubusercontent.com/fadeawaylove/article-images/master/WX20200823-214438%402x.png)

测试故障转移：
手动关掉`redis-master`容器，可以看到哨兵重新选举了新的主redis服务器，并且切换了对应信息。
![https://raw.githubusercontent.com/fadeawaylove/article-images/master/WX20200823-214456%402x.png](https://raw.githubusercontent.com/fadeawaylove/article-images/master/WX20200823-214456%402x.png)