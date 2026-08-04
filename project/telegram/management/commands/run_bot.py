import asyncio
import os

from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message,FSInputFile
from telegram.models import TelegramUser
import pyautogui

router = Router()


@sync_to_async
def save_user_to_db(user_id, username, first_name, last_name):
    obj, created = TelegramUser.objects.get_or_create(
        telegram_id=user_id,
        defaults={
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "is_active": True,
        },
    )
    if not created and not obj.is_active:
        obj.is_active = True
        obj.save(update_fields=["is_active"])
    return created


@router.message(CommandStart())
async def start_handler(message: Message):
    created = await save_user_to_db(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
    )

    if created:
        await message.answer(
            "Xoş gəldin! ✅ Qeydiyyatdan keçdin.\n"
            "Sayt scrape olunan kimi sənə bildiriş gələcək."
        )
    else:
        await message.answer("Yenidən xoş gəldin! Artıq qeydiyyatdasan 👍")


@router.message(Command('screen'))
async def screen_handler(message: Message):
    pyautogui.screenshot('screen.png')

    photo = FSInputFile('screen.png')

    await message.answer_photo(photo,caption="Cari ekran görüntüsü")



class Command(BaseCommand):
    help = "Telegram botu polling rejimində işə salır"

    def handle(self, *args, **options):
        asyncio.run(self.run())

    async def run(self):
        bot_token = '8815856294:AAEMkWNwD9uzkb1tYD_BA7dHv5Dp_-vyV8k'
        if not bot_token:
            self.stderr.write(self.style.ERROR("BOT_TOKEN tapılmadı! .env yoxla."))
            return

        bot = Bot(token=bot_token)
        dp = Dispatcher()
        dp.include_router(router)

        self.stdout.write(self.style.SUCCESS("Bot işə düşdü, dinləyir..."))
        await dp.start_polling(bot)