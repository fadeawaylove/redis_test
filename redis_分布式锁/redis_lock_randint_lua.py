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
