import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPEN_AI_API_KEY")
openai.api_base = "https://api.openai.com/v1/chat/"


def chat_gpt_interface(message: str):
    chat_completion = openai.Completion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message}],
        stream=True,
    )

    answer = []

    if isinstance(chat_completion, dict):
        # not stream
        print(chat_completion.choices[0].message.content)
    else:
        # stream
        for token in chat_completion:
            content = token["choices"][0]["delta"].get("content")
            if content != None:
                # print(content, end="", flush=True)
                answer.append(content)

    return "".join(answer)


if __name__ == "__main__":
    msg = """Какую модель выбрать для суммаризации сообщений из чата,
    выделения общих тем и смыслов, без дополнительного обучения: 
    gpt-3.5-turbo-instruct или gpt-3.5-turbo"""
    print(chat_gpt_interface(msg))
