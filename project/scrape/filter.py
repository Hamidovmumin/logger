from django.core.cache import cache

CACHE_KEY = "emlaksat:known_urls"
STATUS_KEY = "emlaksat_status"

def filter_new_properties(properties):
    """
    Fetch olunan URL-ləri cache-dəki bilinən URL-lərlə müqayisə edir.
    - Cache-də olmayanlar -> yeni elan sayılır
    - Cache-də olan, amma bu fetch-də olmayanlar -> pəncərədən çıxıb, silinir
    """
    current_urls = {p["url"] for p in properties}

    known_urls = cache.get(CACHE_KEY) or set()

    # Yeni elanlar: cache-də olmayanlar
    new_properties = [p for p in properties if p["url"] not in known_urls]
    print(f"New properties: {len(new_properties)}")
    # Yenilənmiş set: yalnız bu fetch-də olan URL-lər qalır
    # (yəni pəncərədən çıxanlar avtomatik aradan götürülür)
    updated_urls = known_urls & current_urls  # kəsişmə - hələ mövcud olanlar

    cache.set(CACHE_KEY, updated_urls, timeout=None)

    status = cache.get(STATUS_KEY)

    if status is None:
        status = {
            "scrape_count": 0,
            "checked_count": 0,
            "new_count": 0,
        }

    status["scrape_count"] += 1
    status["checked_count"] += len(properties)
    status["new_count"] += len(new_properties)
    cache.set(STATUS_KEY, status, timeout=None)

    return new_properties


def mark_as_scraped(properties):

    new_urls = {p["url"] for p in properties if p.get("url")}
    if not new_urls:
        return

    known_urls = cache.get(CACHE_KEY) or set()
    known_urls |= new_urls  # birləşdirmə

    cache.set(CACHE_KEY, known_urls, timeout=None)