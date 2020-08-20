"""
比如对用户一段时间内特定行为次数限流
"""
import redis
import time

client = redis.StrictRedis()

USER_NAME = "xiaoming"


def is_action_allowed(uid, action, period, count):
    key = "%s-%s" % (uid, action)
    now_ts = int(time.time() * 1000)
    action_count = client.zcount(key, now_ts - period, now_ts)
    print(action_count)
    if action_count >= count:
        return False
    with client.pipeline() as pipe:
        pipe.zadd(key, {now_ts: now_ts})
        pipe.zremrangebyscore(key, 0, now_ts - period)
        pipe.expire(key, period + 1)
        pipe.execute()
    return True


if __name__ == '__main__':
    for i in range(20):
        ret = is_action_allowed(USER_NAME, "reply", 5000, 5)
        print("第%s次数尝试，结果%s" % (i + 1, ret))
        time.sleep(0.5)