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
from working_with_db import (
    add_data_to_db,
    get_or_create_db,
    select_all_data_from_db_all_time,
    select_all_messages_from_db_all_time,
    select_all_messages_from_db_today,
    select_last_n_messages_from_db,
)

from gpt4_interface import gpt4_interface
from literals import WELCOME_MESSAGE, START_SUMMARIZE_MESSAGE

load_dotenv()

DEBUG = True

DB_NAME = os.getenv("DB_NAME")
MESSAGES_IN_BUFFER = os.getenv("MESSAGES_IN_BUFFER")
TIME_TO_PRINT = os.getenv("TIME_TO_PRINT")
TIME_INTERVAL_MIN = os.getenv("TIME_INTERVAL_MIN")
MAX_SUMMARIZE_MESSAGES = os.getenv("MAX_SUMMARIZE_MESSAGES")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TOKEN = getenv("BOT_TOKEN")
bot = Bot(os.getenv("TG_API_TOKEN"), parse_mode=ParseMode.HTML)

dp = Dispatcher()

participants_messages = []
chat_id_allowed = set()
queue = set()


def time_to_summarization():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")

    if DEBUG:
        print(f"{current_time=}")

    return current_time == TIME_TO_PRINT
    # return now.minute % TIME_INTERVAL_MIN == 0 and now.second == 0


def validation(message):
    return message.chat.id in chat_id_allowed and message.from_user.id == ADMIN_CHAT_ID


async def summarize(chat_id, messages):
    if len(messages) > 0:
        participants_messages_str = " ".join(map(str, messages))
        summarization_result = gpt4_interface(
            f"{START_SUMMARIZE_MESSAGE} {participants_messages_str}"
        )

        await bot.send_message(
            chat_id,
            f"Данные для суммаризации:"
            f"\n{messages}\n\nОтвет:\n{summarization_result}",
        )
    else:
        bot.send_message(
            chat_id,
            f"Недостаточно данных для суммаризации - количество сообщений должно быть больше 1. Сейчас: {len(messages)=}",
        )


async def summarize_all_messages_today(chat_id):
    con = sl.connect(DB_NAME)
    messages_today = select_all_messages_from_db_today(con, chat_id)
    await summarize(chat_id, messages_today)
    con.close()


@dp.message(Command("summarize_last_n_messages"))
async def command_summarize_last_n_messages(message: types.Message):
    if validation:
        con = sl.connect(DB_NAME)
        add_all_messages_in_buffer_to_db()
        count = message.text.split()[1]
        print(f"{count=}")
        chat_id = message.chat.id
        if int(count) < MAX_SUMMARIZE_MESSAGES:
            last_n_messages = select_last_n_messages_from_db(con, count, chat_id)
            await summarize(chat_id, last_n_messages)
        else:
            await message.answer(
                f"Вы хотите сделать суммаризацию сообщений, количество которых превышает допустимое значение - {MAX_SUMMARIZE_MESSAGES}."
                f"Уменьшите число и повторите попытку."
            )
        con.close()


@dp.message(Command("answer_to_question"))
async def answer_to_question(message: types.Message):
    if validation:
        message_text = message.text.split().pop(0)

        if DEBUG:
            print(f"{message_text=}")
        answer = gpt4_interface(message_text)

        await bot.send_message(
            message.chat.id, f"Вопрос:\n{message.text}\n\nОтвет:\n{answer}"
        )


@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    if validation:
        """
        This handler receives messages with `/start` command
        """
        if message.chat.id not in queue:
            await message.answer(
                f"Hello, {hbold(message.from_user.full_name)}\nТрекер для чата {message.chat.id} запущен"
            )
            queue.add(message.chat.id)

            if DEBUG:
                print(f"{queue=}")

            while True:
                await asyncio.sleep(1)

                chat_id_outer = message.chat.id

                if time_to_summarization():
                    try:
                        add_all_messages_in_buffer_to_db()
                        for chat_id in queue:
                            chat_id_outer = chat_id
                            print(f"{chat_id=}")
                            await summarize_all_messages_today(chat_id_outer)
                            await asyncio.sleep(5)
                    except exceptions.TelegramBadRequest:
                        await bot.send_message(
                            chat_id_outer, f"{exceptions.TelegramBadRequest=}"
                        )
                        print("Telegram server says - Bad Request: message is too long")
                    finally:
                        await asyncio.sleep(5)
        else:
            await message.answer(f"Трекер для чата {message.chat.id} уже запущен")


@dp.message(Command("stop"))
async def command_start_handler(message: Message) -> None:
    if validation:
        """
        This handler receives messages with `/stop` command
        """
        if message.chat.id in queue:
            queue.remove(message.chat.id)

            if DEBUG:
                print(f"{queue=}")

            await message.answer(f"Трекер для чата {message.chat.id} удален")


@dp.message(Command("add_current_chat_to_allowed"))
async def cmd_add_current_chat_to_allowed(message: types.Message):
    if validation:
        try:
            chat_id_allowed.append(message_text.chat.id)
            await message.answer(f"Добавлен новый разрешенный чат: {message_text}")

            if DEBUG:
                print(f"{chat_id_allowed=}")
        except TypeError as e:
            if DEBUG:
                await message.answer(f"Ошибка {e}")
    else:
        await message.answer(f"NOT ALLOWED")


@dp.message(Command("remove_current_chat_from_allowed"))
async def remove_current_chat_from_allowed(message: types.Message):
    if validation:
        try:
            chat_id_allowed.delete(message_text)
            await message.answer(f"Чат удален из списка: {message_text}")

            if DEBUG:
                print(f"{chat_id_allowed=}")
        except TypeError as e:
            if DEBUG:
                await message.answer(f"Ошибка {e}")
    else:
        await message.answer(f"NOT ALLOWED")


@dp.message(Command("show_list"))
async def cmd_show_list(message: types.Message):
    if validation:
        if DEBUG:
            con = sl.connect(DB_NAME)
            data = select_all_messages_from_db_today(con, message.chat.id)
            print(data)
            await message.answer(f"{data=}")
            con.close()
        else:
            await message.answer(f"Режим отладки выключен - {DEBUG=}")


def add_all_messages_in_buffer_to_db():
    con = sl.connect(DB_NAME)
    add_data_to_db(con, participants_messages)
    participants_messages.clear()
    con.close()


def save_message(message: types.Message) -> None:
    tuple_msg = (
        message.message_id,
        message.from_user.id,
        message.chat.id,
        message.from_user.first_name,
        message.date.isoformat(sep=" ", timespec="seconds"),
        message.text,
    )

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
