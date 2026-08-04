from telegram.utils import notify_all_users
from django.core.cache import cache
from celery import shared_task
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

STATUS_KEY = "emlaksat_status"
baku_tz = ZoneInfo("Asia/Baku")


@shared_task(name="scrape.message_bot.get_message_users")
def get_message_users():
    stats = cache.get(STATUS_KEY)
    now = datetime.now(baku_tz)
    three_hours_ago = now - timedelta(hours=3)
    message = (
        "✅ Sayt uğurla scrape olundu, yeni datalar DB-yə əlavə edildi!\n\n"
        "🌐 Mənbə: emlaksat.az\n\n"
        f"🕒 Hesabat dövrü:\n"
        f"{three_hours_ago.strftime('%H:%M')} - {now.strftime('%H:%M')}\n\n"
        f"🔄 Scrape sayı: {stats['scrape_count']}\n"
        f"🔍 Yoxlanılan elan: {stats['checked_count']}\n"
        f"🆕 Yeni elan: {stats['new_count']}\n"
    )

    notify_all_users(message)

    cache.set(
        STATUS_KEY,
        {
            "scrape_count": 0,
            "checked_count": 0,
            "new_count": 0,
        },
        timeout=None,
    )
