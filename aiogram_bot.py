import asyncio
import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import sqlite3 as sl
import logging
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
    select_all_messages_from_db_for_specific_date,
    select_last_n_messages_from_db,
)

# from gpt4_interface import gpt4_interface
from chat_gpt_open_ai_interface import chat_gpt_interface
from literals import WELCOME_MESSAGE, START_SUMMARIZE_MESSAGE

logging.basicConfig(
    level=logging.DEBUG,
    filename="program.log",
    format="%(asctime)s, %(levelname)s, %(message)s, %(name)s, %(filename)s, %(funcName)s, %(lineno)d",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('my_logger.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

load_dotenv()

DEBUG = bool(int(os.getenv("DEBUG")))
DB_NAME = os.getenv("DB_NAME")
MESSAGES_IN_BUFFER = int(os.getenv("MESSAGES_IN_BUFFER"))
TIME_TO_PRINT = os.getenv("TIME_TO_PRINT")
TIME_INTERVAL_MIN = int(os.getenv("TIME_INTERVAL_MIN"))
MAX_SUMMARIZE_MESSAGES = int(os.getenv("MAX_SUMMARIZE_MESSAGES"))
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID").split()
TOKEN = getenv("BOT_TOKEN")
bot = Bot(os.getenv("TG_API_TOKEN"), parse_mode=ParseMode.HTML)

dp = Dispatcher()

participants_messages = []
chat_id_allowed = set()
queue = set()


def validation(message):
    if (
        message.chat.id not in chat_id_allowed
        and message.from_user.id not in ADMIN_CHAT_ID
    ):
        msg = "Access denied"
        logging.INFO(f"{msg=} {message.chat.id=} {message.from_user.id=}")
        message.answer(msg)
    else:
        return True


def auth(func):
    async def wrapper(message: types.Message):
        if validation(message):
            return await func(message)

    return wrapper


def llm_interface(message: str) -> str:
    """
    in this function, the interface for interacting with llm models is selected
    (at the moment there is an official one from open ai and an unofficial one from gpt4
    """

    return chat_gpt_interface(message)
    # return gpt4_interface(message)


def time_to_summarization():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")

    if DEBUG:
        print(f"{current_time=}")

    return current_time == TIME_TO_PRINT
    # return now.minute % TIME_INTERVAL_MIN == 0 and now.second == 0


async def summarize(chat_id, messages):
    if len(messages) > 0:
        participants_messages_str = " ".join(map(str, messages))
        summarization_result = llm_interface(
            f"{START_SUMMARIZE_MESSAGE} {participants_messages_str}"
        )

        msg_today_header = f"#kintolayliGPTsummarize\nВыжимка беседы за **{datetime.datetime.now().strftime('%d.%m.%Y')}**\n\n"

        if DEBUG:
            test_msg = f"Данные для суммаризации:\n{messages}\n\nОтвет:\n{summarization_result}"
            answer_msg = f"{msg_today_header}{test_msg}"
        else:
            answer_msg = f"{msg_today_header}{summarization_result}"

        await bot.send_message(chat_id, answer_msg)
    else:
        await bot.send_message(
            chat_id,
            f"Недостаточно данных для суммаризации - количество сообщений должно быть больше 1. Сейчас: {len(messages)=}",
        )


async def summarize_all_messages_today(chat_id):
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    con = sl.connect(DB_NAME)
    messages_today = select_all_messages_from_db_for_specific_date(con, chat_id, date)
    await summarize(chat_id, messages_today)
    con.close()

async def summarize_all_messages_from_date(chat_id, date):
    con = sl.connect(DB_NAME)
    messages_today = select_all_messages_from_db_for_specific_date(con, chat_id, date)
    await summarize(chat_id, messages_today)
    con.close()

@dp.message(Command("summarize_messages_from_specific_date"))
@auth
async def command_summarize_messages_from_specific_date(message: types.Message):
    con = sl.connect(DB_NAME)
    add_all_messages_in_buffer_to_db()
    date = message.text[len("summarize_messages_from_specific_date") + 2 : :].strip()

    if DEBUG:
        print(f"{date}")

    chat_id = message.chat.id
    if int(date)  < MAX_SUMMARIZE_MESSAGES:
        messages_from_date = summarize_all_messages_from_date(con, date, chat_id)
        await summarize(chat_id, messages_from_date)
    else:
        await message.answer(
            f"Вы хотите сделать суммаризацию сообщений, количество которых превышает допустимое значение - {MAX_SUMMARIZE_MESSAGES}."
            f"Уменьшите число и повторите попытку."
        )
    con.close()


@dp.message(Command("summarize_last_n_messages"))
@auth
async def command_summarize_last_n_messages(message: types.Message):
    con = sl.connect(DB_NAME)
    add_all_messages_in_buffer_to_db()
    count = message.text[len("summarize_last_n_messages") + 2 : :].strip()

    if DEBUG:
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
@auth
async def answer_to_question(message: types.Message):
    message_text = message.text[len("answer_to_question") + 2 : :].strip()

    if DEBUG:
        print(f"{message_text=}")

    answer = gpt4_interface(message_text)

    await bot.send_message(
        message.chat.id, f"Вопрос:\n{message_text}\n\nОтвет:\n{answer}"
    )


@dp.message(Command("start"))
@auth
async def command_start_handler(message: Message) -> None:
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
                    print(
                        "Telegram server says - Bad Request: message is too long"
                    )
                finally:
                    await asyncio.sleep(5)
    else:
        await message.answer(f"Трекер для чата {message.chat.id} уже запущен")


@dp.message(Command("stop"))
@auth
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/stop` command
    """
    if message.chat.id in queue:
        queue.remove(message.chat.id)

        if DEBUG:
            print(f"{queue=}")

        await message.answer(f"Трекер для чата {message.chat.id} удален")


@dp.message(Command("add_current_chat_to_allowed"))
@auth
async def cmd_add_current_chat_to_allowed(message: types.Message):
    try:
        chat_id_allowed.append(message_text.chat.id)
        await message.answer(f"Добавлен новый разрешенный чат: {message_text}")

        if DEBUG:
            print(f"{chat_id_allowed=}")
    except TypeError as e:
        if DEBUG:
            await message.answer(f"Ошибка {e}")


@dp.message(Command("remove_current_chat_from_allowed"))
@auth
async def remove_current_chat_from_allowed(message: types.Message):
    try:
        chat_id_allowed.delete(message_text)
        await message.answer(f"Чат удален из списка: {message_text}")

        if DEBUG:
            print(f"{chat_id_allowed=}")
    except TypeError as e:
        if DEBUG:
            await message.answer(f"Ошибка {e}")


@dp.message(Command("show_list"))
@auth
async def cmd_show_list(message: types.Message):
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    con = sl.connect(DB_NAME)
    data = select_all_messages_from_db_for_specific_date(con, message.chat.id, date)
    print(data)
    await message.answer(f"{data=}")
    con.close()


def add_all_messages_in_buffer_to_db():
    con = sl.connect(DB_NAME)
    add_data_to_db(con, participants_messages)
    participants_messages.clear()
    con.close()


def save_message(message: types.Message) -> None:
    # добавляем смещение по часовому поясу GMT +3
    date = message.date + datetime.timedelta(hours=3)

    tuple_msg = (
        message.message_id,
        message.from_user.id,
        message.chat.id,
        message.from_user.first_name,
        date.isoformat(sep=" ", timespec="seconds"),
        message.text,
    )
    if DEBUG:
        print(tuple_msg)

    participants_messages.append(tuple_msg)
    if len(participants_messages) >= MESSAGES_IN_BUFFER:
        add_all_messages_in_buffer_to_db()


@dp.message()
async def echo_handler(message: types.Message) -> None:
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
        await logging.error(error, exc_info=True)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    con = sl.connect(DB_NAME)
    get_or_create_db(con)

    chat_id_allowed = set(os.getenv("CHAT_ID_ALLOWED").split())

    print(chat_id_allowed)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
