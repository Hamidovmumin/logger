from django.core.cache import cache

from properties.models import Property, Reservation, Review


def dashboard_sidebar_counts(request):
    if not request.user.is_authenticated:
        return {}

    properties_count = Property.objects.count()
    reservations_count = Reservation.objects.count()
    reviews_count = Review.objects.filter(
        is_allowed=False).count()  # gələn/pending rəylər

    return {
        'sidebar_properties_count': properties_count,
        'sidebar_reservations_count': reservations_count,
        'sidebar_reviews_count': reviews_count,
    }


def count_my_favourites(request):
    session_key = request.session.session_key

    if not session_key:
        return {"favourite_count": 0}

    cache_key = f"favourites:{session_key}"
    favourites = cache.get(cache_key, [])

    return {
        "favourite_count": len(favourites)
    }