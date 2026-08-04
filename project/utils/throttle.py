from django.core.cache import cache
from utils.ip_address import get_ip

def check_throttle(
        request,
        endpoint:str,
        limit:int,
        timeout:int,
        block_time:int
)->bool:
    ip = get_ip(request)

    count_key = f"rl:{endpoint}:count:{ip}"
    block_key = f"rl:{endpoint}:block:{ip}"

    if cache.get(block_key):
        return True

    count = cache.get(count_key,0) + 1
    cache.set(count_key,count,timeout)

    if count > limit:
        cache.set(block_key,True,timeout=block_time)
        return True

    return False

