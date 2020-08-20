"""
位图不是特殊的数据结构，它的内容其实就是普通的字符串
实际使用：可以用于记录用户注册以来每天的签到状态
"""
import redis
import random

USER = "user-xiaoming"

client = redis.StrictRedis()


def sign_in(day_offset):
    client.setbit(USER, day_offset, 1)


def get_sign_count():
    count = client.bitcount(USER)
    print("总的签到次数：%s" % count)


def get_single_day_sign_status(day_offset):
    return client.getbit(USER, day_offset)


if __name__ == "__main__":
    # 随机生成签到日
    days = random.sample(range(365), k=100)
    for d in days:
        sign_in(d)
    get_sign_count()
    r = get_single_day_sign_status(100)
    print("第一100天是否签到: %s" % r, 100 in days)
    client.delete(USER)
