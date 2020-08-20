"""
同一个任务被多个进程取到后，zrem的时候争抢，没抢到的进程就白去了一次任务，使用lua脚本将zrangebyscore和zrem变为原子操作，进程争抢任务时就不会出现这种浪费了
"""

import time
import uuid
import json
import threading
import random

import redis

client = redis.StrictRedis()

DELAY_QUEUE_NAME = "delay-queue"

def check_msg(key_name):
    lua_script_string = """
    -- 将从有序集合中查并删除变为原子操作
    local value = redis.call("zrangebyscore", KEYS[1], ARGV[1], ARGV[2], "limit", ARGV[3], ARGV[4])
    if ( next(value)==nil )  -- 取值为空
    then
        return nil
    else
        redis.call("zrem", KEYS[1], value[1])
        return value[1]
    end
    """
    lua_script = client.register_script(lua_script_string)
    return lua_script(keys=[key_name], args=[0,time.time(),0, 1])

def add_to_delay():
    msgs = [{"data": i} for i in range(1000)]
    for m in msgs:
        m["id"] = str(uuid.uuid4())
        value = json.dumps(m)
        ts = time.time() + 5
        client.zadd(DELAY_QUEUE_NAME, {value: ts})
        time.sleep(random.randint(1, 4))


def process_delay_msg():
    while True:
        value = check_msg(DELAY_QUEUE_NAME)
        if value:
            print("%s处理消息：%s" % (threading.current_thread().name, value))
        time.sleep(1)


if __name__ == '__main__':
    tasks = [
        threading.Thread(target=add_to_delay),
        threading.Thread(target=add_to_delay),
        threading.Thread(target=add_to_delay),
        threading.Thread(target=process_delay_msg),
        threading.Thread(target=process_delay_msg),
        threading.Thread(target=process_delay_msg),
    ]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()
