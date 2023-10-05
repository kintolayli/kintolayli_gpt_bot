import asyncio
import datetime
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv
from os import getenv

from gpt4_interface import gpt4_interface
from literals import WELCOME_MESSAGE, START_SUMMARIZE_MESSAGE

DEBUG = True
TIME_TO_PRINT = '21:40:00'
MESSAGE_TIME = datetime.time(hour=19, minute=36, second=0)
TIME_INTERVAL_MIN = 5

load_dotenv()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(os.getenv("TG_API_TOKEN"), parse_mode=ParseMode.HTML)
dp = Dispatcher()

participants = {}
participants_messages = []
my_list = []



async def summarize(message: types.Message, len_messages=None):
    if len(participants_messages) > 5:
        if len_messages is None:
            len_messages = len(participants_messages) * -1
        else:
            len_messages *= -1

        print(f"{len_messages=}")

        last_participants_messages = participants_messages[len_messages::]
        participants_messages_str = ' '.join(map(str, last_participants_messages))
        summarization = gpt4_interface(
            f"{START_SUMMARIZE_MESSAGE} {participants_messages_str}")

        await bot.send_message(message.chat.id, f"Данные для суммаризации:{last_participants_messages}\n\nОтвет:{summarization}")


@dp.message(Command("summarize"))
async def command_summarize(message: types.Message, len_messages):
    summarize(message, len_messages)


@dp.message(Command("answer_to_question"))
async def answer_to_question(message: types.Message):
    answer = gpt4_interface(message.text)

    await bot.send_message(message.chat.id, f"Вопрос:{message.text}\n\nОтвет:{answer}")


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

        # if current_time == TIME_TO_PRINT:
        if now.minute % TIME_INTERVAL_MIN == 0 and now.second == 0:
            try:
                await summarize(message)
                participants_messages.clear()
            except exceptions.TelegramBadRequest:
                print("Telegram server says - Bad Request: message is too long")
            finally:
                await asyncio.sleep(5)


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



@dp.message()
async def echo_handler(message: types.Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        save_message(message)

        if DEBUG:
            print(participants_messages)
            print(f"Размер масcива:{len(participants_messages)}")
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
