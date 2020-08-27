## 缓存穿透
缓存穿透，是指查询一个数据库一定不存在的数据。正常的使用缓存流程大致是，数据查询先进行缓存查询，如果key不存在或者key已经过期，再对数据库进行查询，并把查询到的对象，放进缓存。如果数据库查询对象为空，则不放进缓存。例如查询用户id<0的数据，一般系统中用户id都是大于0的，这样每次查询都穿透了缓存，直接到数据库全表扫描。

### 缓存空值
将查询到的空值也缓存起来，这样即使是数据库中肯定不存在的数据，也不会直接请求到数据库
```python
import time
import redis

client = redis.StrictRedis()


def get_user_info(uid):
    key = "user_info:%s" % uid
    user_info = client.get(key)
    if not user_info:
        user_info = query_user_info_from_mysql(uid)
        if not user_info:
            client.set(key, "None", ex=60)
    else:
        user_info = user_info.decode()
    return user_info


def query_user_info_from_mysql(uid):
    # 模拟从数据库查询
    if uid < 0:
        time.sleep(0.1)
        return None
    return {"name": "张三", "age": 18}


if __name__ == '__main__':
    for i in range(-10, 0):
        info = get_user_info(i)
        print(info)

```

问题：

增加了额外缓存空数据的开销，如果遭到恶意攻击，有大量的空值缓存

### 布隆过滤器
将存在的所有用户对应的信息指纹存到布隆过滤器中，请求过来时，先查询信息指纹是否存在于布隆过滤器，不存在直接返回空，存在则进行缓存和数据库的查找。

```python
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

```

问题：

要注意数据库中数据和布隆过滤器指纹信息的一致性问题，如果出现布隆过滤器中不存在但是实际库中存在的问题就不好了。
另外布隆过滤器还有一定的几率误判，将不存在的数据误判为存在，不过这个一般影响不大。

## 缓存击穿
当热点数据key失效了，同一时间大量请求这个热点数据，就会都怼到数据库

模拟击穿：
```python
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

```

解决：

可以使用一个互斥锁，当redis查不到时，取竞争这个锁，获取锁后从库中查询热点数据并设置缓存，获取不到这个锁说明缓存正在被设置中，可以尝试几次从缓存中获取热点数据
```python
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

```

## 缓存雪崩
所谓缓存雪崩就是在某一个时刻，缓存集大量失效。所有流量直接打到数据库上，对数据库造成巨大压力。

解决：
1. 缓存标记：给每一个缓存数据增加相应的缓存标记，记录缓存的是否失效，如果缓存标记失效，则更新数据缓存
2. 缓存过期时间错开：设置缓存时间错开，可以在设置过期时间的时候，加一个一定范围内的随机值来错开
3. 加锁/队列：这样虽然能降低数据库压力，但是同时，响应也很慢




