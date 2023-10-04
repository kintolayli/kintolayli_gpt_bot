import os
import pathlib

import telebot
from dotenv import load_dotenv
from gpt4_interface import gpt4_interface

from literals import WELCOME_MESSAGE, INVALID_LINK_MESSAGE

load_dotenv()
bot = telebot.TeleBot(os.getenv("TG_API_TOKEN"))


# Handle '/start' and '/help'
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.send_message(
        chat_id=message.chat.id, text=WELCOME_MESSAGE, parse_mode="Markdown"
    )


# Handle all other messages with content_type 'text' (content_types defaults
# to ['text'])
@bot.message_handler(content_types=["text"])
def echo_message(message):
    text = gpt4_interface(message.text)

    bot.send_message(
        chat_id=message.chat.id,
        text=text,
        parse_mode="Markdown",
    )


bot.infinity_polling()
