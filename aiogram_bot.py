import asyncio
import datetime
import logging
import os
import sys
import sqlite3 as sl
from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv
from os import getenv
from working_with_db import (add_data_to_db, get_or_create_db,
                             select_all_data_from_db_all_time,
                             select_all_messages_from_db_all_time,
                             select_all_messages_from_db_today,
                             select_last_n_messages_from_db,
                             )

from gpt4_interface import gpt4_interface
from literals import WELCOME_MESSAGE, START_SUMMARIZE_MESSAGE

load_dotenv()

DB_NAME = 'db.db'
MESSAGES_IN_BUFFER = 5
DEBUG = True
TIME_TO_PRINT = '21:40:00'
MESSAGE_TIME = datetime.time(hour=19, minute=36, second=0)
TIME_INTERVAL_MIN = 5
MAX_SUMMARIZE_MESSAGES = 200

TOKEN = getenv("BOT_TOKEN")
bot = Bot(os.getenv("TG_API_TOKEN"), parse_mode=ParseMode.HTML)
dp = Dispatcher()

participants = {}
participants_messages = []
my_list = []
chat_id_allowed = []

async def summarize(message: types.Message, messages):
    if len(messages) > 2:
        participants_messages_str = ' '.join(map(str, messages))
        summarization_result = gpt4_interface(
            f"{START_SUMMARIZE_MESSAGE} {participants_messages_str}")

        await bot.send_message(message.chat.id, f"Данные для суммаризации:\n{messages}\n\nОтвет:\n{summarization_result}")


async def summarize_all_messages_today(message: types.Message):
    chat_id = message.chat.id
    messages_today = select_all_messages_from_db_today(con, chat_id)
    await summarize(message, messages_today)


@dp.message(Command("summarize_last_n_messages"))
async def command_summarize_last_n_messages(message: types.Message):
    add_all_messages_in_buffer_to_db()
    count = message.text.split()[1]
    chat_id = message.chat.id
    if int(count) < MAX_SUMMARIZE_MESSAGES:
        last_n_messages = select_last_n_messages_from_db(con, count, chat_id)
        await summarize(message, last_n_messages)
    else:
        await message.answer(f"Вы хотите сделать суммаризацию сообщений, количество которых превышает допустимое значение - {MAX_SUMMARIZE_MESSAGES}."
                             f"Уменьшите число и повторите попытку.")


@dp.message(Command("answer_to_question"))
async def answer_to_question(message: types.Message):
    answer = gpt4_interface(message.text)

    await bot.send_message(message.chat.id, f"Вопрос:\n{message.text}\n\nОтвет:\n{answer}")


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
                add_all_messages_in_buffer_to_db()
                await summarize_all_messages_today(message)
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
            await message.answer(f"Добавлен новый разрешенный чат: {message_text}")
        else:
            await message.answer(f"Вы хотите добавить пустое сообщение")
    except TypeError as e:
        await message.answer(f"Ошибка {e}")


@dp.message(Command("show_list"))
async def cmd_show_list(message: types.Message):
    data = select_all_messages_from_db_today(con)
    print(data)

def add_all_messages_in_buffer_to_db():
    add_data_to_db(con, participants_messages)
    participants_messages.clear()

def save_message(message: types.Message) -> None:
    tuple_msg = (message.message_id,
                 message.from_user.id,
                 message.chat.id,
                 message.from_user.first_name,
                 message.date.isoformat(sep=" ", timespec="seconds"),
                 message.text)

    participants_messages.append(tuple_msg)
    if len(participants_messages) >= MESSAGES_IN_BUFFER:
        add_all_messages_in_buffer_to_db()

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
            # print(message)

            print(f"{message.message_id=}")
            print(f"{message.from_user.id=}")
            print(f"{message.chat.id=}")
            print(f"{message.from_user.first_name=}")
            print(f"{message.date=}")
            print(f"{message.text=}")
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    con = sl.connect(DB_NAME)
    get_or_create_db(con)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
