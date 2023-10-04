import asyncio
import datetime
import logging
import os

import telebot

from literals import WELCOME_MESSAGE

# Токен бота, полученный от BotFather
BOT_TOKEN = os.getenv("TG_API_TOKEN")

# ID чата, в который будем отправлять сообщение
CHAT_ID = 'your_chat_id_here'

# Время, в которое будем отправлять сообщение (в UTC)
MESSAGE_TIME = datetime.time(hour=18, minute=35, second=0)

# Инициализируем логгер
logging.basicConfig(level=logging.INFO)

# Создаем объект бота
bot = telebot.TeleBot(token=BOT_TOKEN)

participants = {}


@bot.channel_post_handler(content_types=["text"])
async def save_message(message):
    user_id = message.from_user.id
    if user_id not in participants:
        participants[user_id] = []
    participants[user_id].append(message.text)


async def send_message():
    # Получаем текущее время
    offset = datetime.timedelta(hours=3)
    tz = datetime.timezone(offset, name='МСК')
    current_time = datetime.datetime.now(tz=tz).time()

    print(current_time)
    print(participants)

    # Если текущее время совпадает с временем отправки сообщения
    if current_time == MESSAGE_TIME:
        # Отправляем сообщение в чат
        await bot.send_message(chat_id=CHAT_ID,
                               text=WELCOME_MESSAGE)

        # Логируем отправку сообщения
        logging.info('Сообщение отправлено в чат %s', CHAT_ID)


async def main():
    # Бесконечный цикл
    while True:
        # Ожидаем 1 секунду
        await asyncio.sleep(10)

        # Запускаем функцию отправки сообщения в отдельном таске
        asyncio.create_task(send_message())
        asyncio.create_task(save_message())


if __name__ == '__main__':
    # Запускаем основной цикл
    asyncio.run(main())
