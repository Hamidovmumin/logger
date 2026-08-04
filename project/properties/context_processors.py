from django.core.cache import cache

def count_my_favourites(request):
    session_key = request.session.session_key

    if not session_key:
        return { "favourite_count": 0 }

    cache_key = f"favourites:{session_key}"
    favourites = cache.get(cache_key, [])

    return {
        "favourite_count": len(favourites)
    }