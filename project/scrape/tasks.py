from celery import shared_task
from scrape.filter import filter_new_properties,mark_as_scraped
from scrape.emlaksat_az import scrape_properties_url, save,scrape_properties_detail
from telegram.utils import notify_all_users
from django.core.cache import cache

STATUS_KEY = "emlaksat_status"

@shared_task(name="scrape.tasks.scrape_emlaksat_task")
def scrape_emlaksat_task():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    print("############################")
    print("Scraping başladı...")

    properties = scrape_properties_url()
    # print('#########################################################################')
    # print(f'Saytdan {len(properties)} sayda data götürüldü ✅')
    # print('#########################################################################')
    #
    print('Datalar filterlənir...')
    filter_properties = filter_new_properties(properties)

    print(f'{len(filter_properties)}Datalar tapildi...')

    # if not filter_properties:
    #     print("Yeni elan tapılmadı.")
    #     print("====================================")
    #     return "Yeni elan tapılmadı."
    #
    # print(f"{len(filter_properties)} yeni elan tapıldı. Database-yə yazılır...")
    #
    new_properties=scrape_properties_detail(
        properties=filter_properties,
        headers=headers
    )
    #
    # try:
    #     save(new_properties)
    # except Exception as e:
    #     print(f"Save zamanı xəta baş verdi: {e}")
    #     # cache-ə yazılmır, növbəti dəfə yenidən cəhd olunacaq
    #     raise
    #
    # # yalnız save UĞURLA bitdikdən sonra cache-ə yazılır
    mark_as_scraped(new_properties)
    #
    # print("Scraping bitdi.")


    return f"{len(properties)} property saved."
