"""
请求一个没有的数据，缓存会失效，库中也必定没有这个数据
例如查询用户id<0的数据，一般系统中用户id都是大于0的，这样每次查询都穿透了缓存，直接到数据库全表扫描
"""
import time
import redis

client = redis.StrictRedis()


def get_user_info(uid):
    key = "user_info:%s" % uid
    user_info = client.get(key)
    if not user_info:
        user_info = query_user_info_from_mysql(uid)
        if not user_info:
            client.set(key, "不存在", ex=60)
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
