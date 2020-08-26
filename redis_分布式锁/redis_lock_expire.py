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
