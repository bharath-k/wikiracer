'''
Utils to manage async interaction with redis
'''
import aioredis
import json
from .settings import REDIS_HOST, REDIS_PORT

async def get_redis():
    '''
    Get the global redis instance.
    '''
    global redis_instance
    if not redis_instance:
        redis_instance = await aioredis.create_redis((REDIS_HOST, REDIS_PORT))
    return redis_instance


async def redis_get(key):
    '''
    Fetch data from redis
    '''
    redis = await get_redis()
    data = await redis.get(key)
    # data containing bytes will not be serialized, but this is fine for current use case
    if data:
        return json.loads(data)
    return data


async def redis_set(key, value):
    '''
    Store data in redis
    '''
    redis = await get_redis()
    await redis.set(key, json.dumps(value))
