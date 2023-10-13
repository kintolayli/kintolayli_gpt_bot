FROM python:3.11-slim
LABEL authors="kintolayli"
RUN mkdir /app
COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt --no-cache-dir

COPY aiogram_bot.py /app
COPY chat_gpt_open_ai_interface.py /app
COPY gpt4_interface.py /app
COPY literals.py /app
COPY working_with_db.py /app

WORKDIR /app


ENTRYPOINT ["python3", "aiogram_bot.py"]