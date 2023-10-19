import asyncio
import datetime
import logging
import os
import sqlite3 as sl
import sys
from logging.handlers import RotatingFileHandler
from os import getenv

from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

# from gpt4_interface import gpt4_interface
from chat_gpt_open_ai_interface import chat_gpt_interface
from literals import START_SUMMARIZE_MESSAGE
from working_with_db import (
    add_data_to_db,
    get_or_create_db,
    select_all_messages_from_db_for_specific_date,
    select_last_n_messages_from_db,
)

logging.basicConfig(
    level=logging.DEBUG,
    filename="log.log",
    format="%(asctime)s, %(levelname)s, %(message)s, %(name)s, %(filename)s, %(funcName)s, %(lineno)d",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("log.log", maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

load_dotenv()

DEBUG = bool(int(os.getenv("DEBUG")))
DB_NAME = os.getenv("DB_NAME")
MESSAGES_IN_BUFFER = int(os.getenv("MESSAGES_IN_BUFFER"))
TIME_TO_PRINT = os.getenv("TIME_TO_PRINT")
TIME_INTERVAL_MIN = int(os.getenv("TIME_INTERVAL_MIN"))
MAX_SUMMARIZE_MESSAGES = int(os.getenv("MAX_SUMMARIZE_MESSAGES"))
ALLOWED_USER_ID_LIST = set(map(int, os.getenv("ALLOWED_USER_ID_LIST").split()))
ALLOWED_CHAT_ID_LIST = set(map(int, os.getenv("ALLOWED_CHAT_ID_LIST").split()))
TOKEN = getenv("BOT_TOKEN")
bot = Bot(os.getenv("TG_API_TOKEN"), parse_mode=ParseMode.HTML)

dp = Dispatcher()

participants_messages = []
queue = set()


async def validation_chat(message: types.Message):
    if message.chat.id not in ALLOWED_CHAT_ID_LIST:
        msg = f"CHAT_ID {message.chat.id} not found in ALLOWED_CHAT_ID_LIST. Access denied."
        logging.info(f"{msg=} {message.chat.id=}")
        await message.answer(msg)
        await asyncio.sleep(5)
    else:
        return True


async def validation_user(message: types.Message):
    if message.from_user.id not in ALLOWED_USER_ID_LIST:
        msg = f"USER_ID {message.from_user.id} not found in ALLOWED_USER_ID_LIST. Access denied."
        logging.info(f"{msg=} {message.from_user.id=}")
        await message.answer(msg)
    else:
        return True


def auth_chat(func):
    async def wrapper(message: types.Message):
        if await validation_chat(message):
            return await func(message)

    return wrapper


def auth_user(func):
    async def wrapper(message: types.Message):
        if await validation_user(message):
            return await func(message)

    return wrapper


def llm_interface(message: str) -> str:
    """
    in this function, the interface for interacting with llm models is selected
    (at the moment there is an official one from open ai and an unofficial one from gpt4
    """

    return chat_gpt_interface(message)
    # return gpt4_interface(message)


def time_to_summarization() -> bool:
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")

    if DEBUG:
        print(f"{current_time=}")

    return current_time == TIME_TO_PRINT


async def summarize(chat_id: int, messages: list, date: str) -> None:
    if len(messages) > 0:
        participants_messages_str = " ".join(map(str, messages))
        summarization_result = llm_interface(
            f"{START_SUMMARIZE_MESSAGE} {participants_messages_str}"
        )

        msg_today_header = (
            f"#kintolayliGPTsummarize\nВыжимка беседы за {hbold(date)}\n\n"
        )

        if DEBUG:
            test_msg = f"Данные для суммаризации:\n{messages}\n\nОтвет:\n{summarization_result}"
            answer_msg = f"{msg_today_header}{test_msg}"
        else:
            answer_msg = f"{msg_today_header}{summarization_result}"

        await bot.send_message(chat_id, answer_msg)
    else:
        await bot.send_message(
            chat_id,
            f"Недостаточно данных для суммаризации - количество сообщений должно быть больше 1. Сейчас: {len(messages)}",
        )


async def select_all_messages_from_date(chat_id: int, date: str) -> list:
    con = sl.connect(DB_NAME)
    messages_today = select_all_messages_from_db_for_specific_date(
        con, chat_id, date
    )
    con.close()
    return messages_today


@dp.message(Command("summarize_messages_from_date"))
@auth_user
async def command_summarize_messages_from_date(message: types.Message) -> None:
    add_all_messages_in_buffer_to_db()
    date = message.text[
           len("summarize_messages_from_specific_date") + 2::
           ].strip()

    if DEBUG:
        print(f"{date}")

    messages_from_date = await select_all_messages_from_date(
        message.chat.id, date
    )
    await summarize(message.chat.id, messages_from_date, date)


@dp.message(Command("summarize_last_n_messages"))
@auth_user
async def command_summarize_last_n_messages(message: types.Message) -> None:
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    con = sl.connect(DB_NAME)
    add_all_messages_in_buffer_to_db()
    count = message.text[len("summarize_last_n_messages") + 2::].strip()

    if DEBUG:
        print(f"{count=}")

    if int(count) < MAX_SUMMARIZE_MESSAGES:
        last_n_messages = select_last_n_messages_from_db(
            con, count, message.chat.id
        )
        await summarize(message.chat.id, last_n_messages, date)
    else:
        await message.answer(
            f"Вы хотите сделать суммаризацию сообщений, количество которых превышает допустимое значение - {MAX_SUMMARIZE_MESSAGES}."
            f"Уменьшите число и повторите попытку."
        )
    con.close()


@dp.message(Command("question"))
@auth_user
async def command_question(message: types.Message) -> None:
    message_text = message.text[len("question") + 2::].strip()

    if DEBUG:
        print(f"{message_text=}")

    if len(message_text) > 0:
        answer = llm_interface(message_text)

        await bot.send_message(
            message.chat.id, f"Вопрос:\n{message_text}\n\nОтвет:\n{answer}"
        )
    else:
        await bot.send_message(
            message.chat.id,
            "Пустое сообщение, напишите вопрос сразу после команды - question {ваш вопрос}",
        )


@dp.message(Command("start"))
@auth_chat
@auth_user
async def command_start_summarize_by_time_every_day(message: Message) -> None:
    """
    This handler receives messages with `/start` command

    """
    if message.chat.id not in queue:

        await message.answer(
            f"Hello, {hbold(message.from_user.full_name)}\nТрекер для чата {message.chat.id} запущен"
        )
        queue.add(message.chat.id)

        while message.chat.id in queue:
            # добавляем смещение по часовому поясу GMT +3
            today_date = datetime.datetime.now()
            today_date_formatted = today_date.strftime("%Y-%m-%d")

            if DEBUG:
                print(f"{queue=}")

            await asyncio.sleep(1)

            if time_to_summarization():
                try:
                    add_all_messages_in_buffer_to_db()

                    if DEBUG:
                        print(f"{message.chat.id=}")

                    messages = await select_all_messages_from_date(
                        message.chat.id,
                        today_date_formatted
                    )
                    await summarize(message.chat.id,
                                    messages,
                                    today_date_formatted)

                    await asyncio.sleep(1)
                except exceptions.TelegramBadRequest:
                    await bot.send_message(
                        message.chat.id, f"{exceptions.TelegramBadRequest=}"
                    )
                    print(
                        "Telegram server says - Bad Request: message is too long"
                    )
                finally:
                    await asyncio.sleep(5)
    else:
        await message.answer(f"Трекер для чата {message.chat.id} уже запущен")


@dp.message(Command("stop"))
@auth_chat
@auth_user
async def command_stop_summarize_by_time_every_day(message: Message) -> None:
    """
    This handler receives messages with `/stop` command
    """
    if message.chat.id in queue:
        queue.remove(message.chat.id)

        if DEBUG:
            print(f"{queue=}")

        await message.answer(f"Трекер для чата {message.chat.id} удален")


@dp.message(Command("add_current_chat_to_allowed"))
@auth_user
async def cmd_add_current_chat_to_allowed(message: types.Message):
    try:
        ALLOWED_CHAT_ID_LIST.add(message.chat.id)
        await message.answer(
            f"Добавлен новый разрешенный чат: {message.chat.id}"
        )

        if DEBUG:
            print(f"{ALLOWED_CHAT_ID_LIST=}")
    except TypeError as error:
        logging.error(error, exc_info=True)
        await message.answer(f"Ошибка {error}")


@dp.message(Command("remove_current_chat_from_allowed"))
@auth_user
async def remove_current_chat_from_allowed(message: types.Message) -> None:
    try:
        ALLOWED_CHAT_ID_LIST.remove(message.chat.id)
        await message.answer(f"Чат удален из списка: {message.chat.id}")

        if DEBUG:
            print(f"{ALLOWED_CHAT_ID_LIST=}")
    except TypeError as error:
        logging.error(error, exc_info=True)
        await message.answer(f"Ошибка {error}")


@dp.message(Command("show_messages_from_date"))
@auth_user
async def cmd_show_messages_from_date(message: types.Message,
                                      date=None) -> None:
    if date is None:
        date = datetime.datetime.now().strftime("%Y-%m-%d")

    print(date)

    con = sl.connect(DB_NAME)

    messages = select_all_messages_from_db_for_specific_date(
        con, message.chat.id, date
    )
    print(messages)

    await message.answer(f"{messages=}")
    con.close()


def add_all_messages_in_buffer_to_db() -> None:
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
        message.date.isoformat(timespec="seconds"),
        message.text,
    )
    if DEBUG:
        print(tuple_msg)

    participants_messages.append(tuple_msg)
    if len(participants_messages) >= MESSAGES_IN_BUFFER:
        add_all_messages_in_buffer_to_db()


@dp.message()
async def message_handler(message: types.Message) -> None:
    """
    Handler that forwards a received message back to the sender.
    Args:
        message (types.Message): The message received.
    Returns:
        None
    """
    try:
        if message.text is not None:
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
    except TypeError as error:
        logging.error(error, exc_info=True)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    con = sl.connect(DB_NAME)
    get_or_create_db(con)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
