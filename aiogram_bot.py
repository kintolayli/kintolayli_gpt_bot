import os
import datetime

from dotenv import load_dotenv

import asyncio
import logging
import sys
from os import getenv
import aioschedule

from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.filters.command import Command
from aiogram import Bot, Dispatcher, types

from gpt4_interface import gpt4_interface
from literals import WELCOME_MESSAGE

DEBUG = False
TIME_TO_PRINT = '21:40:00'

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(os.getenv("TG_API_TOKEN"), parse_mode=ParseMode.HTML)
dp = Dispatcher()

participants = {}
participants_messages = []
my_list = []

ID_USER = 38743669
ID_USER = 6518329630

MESSAGE_TIME = datetime.time(hour=19, minute=36, second=0)
MESSAGE_SUMMARIZATION_TEXT = ("Пожалуйста, суммаризируй и выдели главное из "
                              "этих сообщений: ")


@dp.message(Command("summarize"))
async def summarize(message: types.Message,
                    len_messages=len(participants_messages)):
    last_participants_messages = participants_messages[len_messages::]
    participants_messages_str = ''.join(last_participants_messages)
    summarization = gpt4_interface(
        f"{MESSAGE_SUMMARIZATION_TEXT} {participants_messages_str}")

    await bot.send_message(message.chat.id, summarization)


@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """

    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!")

    while True:
        await asyncio.sleep(1)
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        if DEBUG:
            print(current_time)
        if current_time == TIME_TO_PRINT:
            await summarize(message)


@dp.message(Command("add_to_list"))
async def cmd_add_to_list(message: types.Message):
    try:
        message_text = message.text[len("add_to_list") + 2:]
        if len(message_text) > 0:
            my_list.append(message_text)
            await message.answer(f"Добавлен текст: {message_text}")
        else:
            await message.answer(f"Вы хотите добавить пустое сообщение")
    except TypeError as e:
        await message.answer(f"Ошибка {e}")


@dp.message(Command("show_list"))
async def cmd_show_list(message: types.Message):
    await message.answer(f"Ваш список: {my_list}")


def save_message(message: types.Message) -> None:
    # print(message)
    chat_id = message.from_user.id
    if chat_id not in participants:
        participants[chat_id] = []
    participants[chat_id].append(message.text)

    participants_messages.append(message.text)
    # # Send a copy of the received message
    # # await message.send_copy(chat_id=message.chat.id)


@dp.message()
async def echo_handler(message: types.Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        save_message(message)
        # Send a copy of the received message
        # await message.send_copy(chat_id=message.chat.id)
        # await bot.send_message(message.chat.id, ''.join(participants))
        print(participants_messages)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
