import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("HUGGING_FACE_TOKEN")
openai.api_base = os.getenv("API_BASE")


def gpt4_interface(message: str):
    chat_completion = openai.ChatCompletion.create(
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
    print(gpt4_interface("напиши стишок японский четверостишье"))
