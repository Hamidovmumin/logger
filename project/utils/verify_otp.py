from django.core.cache import cache
from typing import Any

def verify_otp(email:str,code:str)-> bool | str:
    saved_code = cache.get(f"otp:{email}")
    if saved_code is None:
        return False
    if code == saved_code:
        return code

    return False
