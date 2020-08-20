"""
延时队列：可用于当redis分布式锁加锁失败时，转移至延时队列，延后再试
"""

import time
import uuid
import json
import threading
import random

import redis

client = redis.StrictRedis()

DELAY_QUEUE_NAME = "delay-queue"


def add_to_delay():
    msgs = [{"data": i} for i in range(100)]
    for m in msgs:
        m["id"] = str(uuid.uuid4())
        value = json.dumps(m)
        ts = time.time() + 5
        client.zadd(DELAY_QUEUE_NAME, {value: ts})
        time.sleep(random.randint(3, 7))


def process_delay_msg():
    while True:
        value = client.zrangebyscore(DELAY_QUEUE_NAME,
                                     0,
                                     time.time(),
                                     start=0,
                                     num=1)
        if not value:
            time.sleep(1)
            continue
        value = value[0]
        # 获取消息后从集合中删除
        success = client.zrem(DELAY_QUEUE_NAME, value)
        if success:
            print("处理消息：%s" % (value))
        time.sleep(1)


if __name__ == '__main__':
    tasks = [
        threading.Thread(target=add_to_delay),
        threading.Thread(target=process_delay_msg)
    ]
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()
