import os
import time
import requests
from telegram.models import TelegramUser

BOT_TOKEN = '8815856294:AAEMkWNwD9uzkb1tYD_BA7dHv5Dp_-vyV8k'
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"



def notify_all_users(text: str):
    user_ids = TelegramUser.objects.filter(is_active=True).values_list("telegram_id", flat=True)

    for user_id in user_ids:
        try:
            response = requests.post(
                TELEGRAM_API_URL,
                json={"chat_id": user_id, "text": text},
                timeout=5,
            )
            if response.status_code == 403:
                TelegramUser.objects.filter(telegram_id=user_id).update(is_active=False)
            elif not response.ok:
                print(f"Xəta ({user_id}): {response.text}")
        except requests.RequestException as e:
            print(f"Şəbəkə xətası ({user_id}): {e}")

        time.sleep(0.05)