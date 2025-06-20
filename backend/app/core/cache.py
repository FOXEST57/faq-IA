import json
import hashlib
from redis import Redis
from flask import current_app
from functools import wraps

redis_client = None

def get_redis():
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(current_app.config['REDIS_URL'])
    return redis_client

def cache_response(ttl=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(func, *args, **kwargs)
            redis = get_redis()
            cached = redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            result = func(*args, **kwargs)
            redis.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

def generate_cache_key(func, *args, **kwargs):
    arg_str = '|'.join(str(arg) for arg in args)
    kwarg_str = '|'.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    func_name = func.__name__
    return f"cache:{func_name}:{hashlib.sha256((arg_str + kwarg_str).encode()).hexdigest()}"