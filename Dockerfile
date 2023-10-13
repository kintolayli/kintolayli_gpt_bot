FROM python:3.11-slim
LABEL authors="kintolayli"

RUN mkdir /app
COPY . /app
RUN pip3 install -r /app/requirements.txt --no-cache-dir

WORKDIR /app


ENTRYPOINT ["python3", "aiogram_bot.py"]