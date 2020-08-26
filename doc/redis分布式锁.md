## 分布式锁
“分布式锁”是用来解决分布式应用中“并发冲突”的一种常用手段,一般用于解决多进程共享资源的问题。使用redis来实现分布式锁核心就是`setnx`命令，`setnx key value`当这个`key`已经被设置过了就会返回0，否则返回1。

## 简单实现
```python
"""
redis分布式锁简单实现
"""

import time
import threading
import redis

client = redis.StrictRedis()

LOCK_NAME = "demo_lock"


def work(seconds):
    lock = None
    while lock is None:
        lock = client.set(LOCK_NAME, "锁", nx=True)
        time.sleep(0.1)
    name = threading.current_thread().name
    print("%s get lock:%s, seconds:%s" % (name, lock, seconds))
    time.sleep(seconds)
    print("%s release lock: %s" % (name, client.delete(LOCK_NAME)))


if __name__ == '__main__':
    tasks = [threading.Thread(target=work, args=[4]),
             threading.Thread(target=work, args=[1]),
             threading.Thread(target=work, args=[2]),
             threading.Thread(target=work, args=[3])]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()

```
输出：
```shell script
Thread-3 get lock:True, seconds:2
Thread-3 release lock: 1
Thread-4 get lock:True, seconds:3
Thread-4 release lock: 1
Thread-1 get lock:True, seconds:4
Thread-1 release lock: 1
Thread-2 get lock:True, seconds:1
Thread-2 release lock: 1
```

问题：

可以看到不同任务实现了串行运行，后面的任务必须等待拿到锁才能执行，但是这样会有一个问题，如果有个任务卡住很久就会导致其它的所有任务都卡住。

## 带过期时间
只需要在set的时候带上ex参数
```python
import time
import threading
import redis

client = redis.StrictRedis()

LOCK_NAME = "demo_lock"


def work(seconds):
    lock = None
    while lock is None:
        lock = client.set(LOCK_NAME, "锁", ex=5, nx=True)
        time.sleep(0.1)
    name = threading.current_thread().name
    print("%s get lock:%s, seconds:%s" % (name, lock, seconds))
    time.sleep(seconds)
    print("%s release lock: %s" % (name, client.delete(LOCK_NAME)))


if __name__ == '__main__':
    tasks = [threading.Thread(target=work, args=[4]),
             threading.Thread(target=work, args=[1]),
             threading.Thread(target=work, args=[2]),
             threading.Thread(target=work, args=[3])]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()

```

输出：
```shell script
Thread-2 get lock:True, seconds:1
Thread-2 release lock: 1
Thread-4 get lock:True, seconds:3
Thread-4 release lock: 1
Thread-1 get lock:True, seconds:4
Thread-1 release lock: 1
Thread-3 get lock:True, seconds:2
Thread-3 release lock: 1

```
将代码中某个任务的时间设置为大于5后的输出：
```shell script
Thread-3 get lock:True, seconds:2
Thread-3 release lock: 1
Thread-1 get lock:True, seconds:6
Thread-4 get lock:True, seconds:3
Thread-1 release lock: 1
Thread-2 get lock:True, seconds:1
Thread-2 release lock: 1
Thread-4 release lock: 0

```

问题：

这样当一个任务卡住，过期时间一到其它任务也可以执行，但是这样又引入了新问题，当任务A执行时间太长，过期时间到了，锁被自动释放了，然后任务B获取到锁开始执行，A执行完后释放的锁会是B的，这样就会出现两个任务同时执行的情况

## 随机数
Redis 的分布式锁不能解决超时问题，如果在加锁和释放锁之间的逻辑执行的太长，以至于超出了锁的超时限制，就会出现问题。因为这时候第一个线程持有的锁过期了，临界区的逻辑还没有执行完，这个时候第二个线程就提前重新持有了这把锁，导致临界区代码不能得到严格的串行执行。
一个安全一点的方法是设置锁的时候value设置为一个随机数，这样可以避免任务A的锁被任务B释放这种问题，锁超时问题无法完美解决。

```python

import time
import threading
import redis

client = redis.StrictRedis()

LOCK_NAME = "demo_lock"


def work(seconds):
    lock = None
    while lock is None:
        current_time = time.time()
        lock = client.set(LOCK_NAME, current_time, ex=5, nx=True)
        time.sleep(0.1)
    name = threading.current_thread().name
    print("%s get lock:%s, seconds:%s" % (name, lock, seconds))
    time.sleep(seconds)
    current_time2 = client.get(LOCK_NAME)
    if current_time == float(current_time2):
        print("%s release lock: %s" % (name, client.delete(LOCK_NAME)))


if __name__ == '__main__':
    tasks = [threading.Thread(target=work, args=[6]),
             threading.Thread(target=work, args=[1]),
             threading.Thread(target=work, args=[2]),
             threading.Thread(target=work, args=[3])]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()

```

输出：
```shell script
Thread-3 get lock:True, seconds:2
Thread-3 release lock: 1
Thread-2 get lock:True, seconds:1
Thread-2 release lock: 1
Thread-1 get lock:True, seconds:6
Thread-4 get lock:True, seconds:3
Thread-4 release lock: 1
```

问题：

可以看到确实不会出现一个任务释放另一个任务锁的情况，但是读和删除之间不是原子操作，如果读取判断一致，但是此时锁过期被其它任务获取，就会删除其它任务的锁，改进的话可以使用lua脚本。

改进：
```python
import time
import threading
import redis

client = redis.StrictRedis()

LOCK_NAME = "demo_lock"

lua_script_string = """
local value = redis.call("get", KEYS[1])
if ( value==ARGV[1] )
then
    redis.call("del", KEYS[1])
    return 1
else
    return 0
end
"""
lua_script = client.register_script(lua_script_string)


def work(seconds):
    lock = None
    while lock is None:
        current_time = time.time()
        lock = client.set(LOCK_NAME, current_time, ex=5, nx=True)
        time.sleep(0.1)
    name = threading.current_thread().name
    print("%s get lock:%s, seconds:%s" % (name, lock, seconds))
    time.sleep(seconds)

    ret = lua_script(keys=[LOCK_NAME], args=[current_time])
    print("%s release lock: %s" % (name, ret))


if __name__ == '__main__':
    tasks = [threading.Thread(target=work, args=[6]),
             threading.Thread(target=work, args=[1]),
             threading.Thread(target=work, args=[2]),
             threading.Thread(target=work, args=[3])]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()

```

结果：
```shell script
Thread-1 get lock:True, seconds:6
Thread-4 get lock:True, seconds:3
Thread-1 release lock: 0
Thread-4 release lock: 1
Thread-2 get lock:True, seconds:1
Thread-2 release lock: 1
Thread-3 get lock:True, seconds:2
Thread-3 release lock: 1

```

