import redis
import time
import threading

client = redis.StrictRedis()

QUEUE_NAME = "message-queue"

def publish():
    while True:
        client.lpush(QUEUE_NAME, time.time())
        time.sleep(1)

def consume():
    while True:
        data = client.lpop(QUEUE_NAME)
        if data is not None:
            print("consume data: %s" % data.decode())
        time.sleep(0.1)

if __name__ == '__main__':
    tasks = []
    tasks.append(threading.Thread(target=publish))
    tasks.append(threading.Thread(target=consume))
    for t in tasks:
        t.start()
    for t in tasks:
        t.join()


