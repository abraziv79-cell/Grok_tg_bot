import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import F
import httpx
from collections import defaultdict
import json
import os

# ←←←←← ВСТАВЬ СЮДА СВОИ ТОКЕНЫ ←←←←←
TELEGRAM_TOKEN = os.getenv("8205674354:AAGbgMdz30UjZX3SmE-7auVyw-X3Peim7vE")
GROK_API_KEY = os.getenv("xai-NbYw4PF3b52qbyZarsk9MUPtaZp9iiUBAEyVtMquZpOZP2Uc5S6LYxnGizDuu6vqg9PyLWnNNJYZWYh5")
# →→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→

GROK_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-4.1"  # или grok-2, grok-2-latest — что у тебя в дашборде активно

bot = Bot(token=TELEGRAM_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Память диалогов: user_id → список сообщений
history = defaultdict(list)

MAX_HISTORY = 20  # сколько последних сообщений хранить (10 пар вопрос-ответ ≈ 20)


def get_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("🧹 Очистить память"))
    return keyboard


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Здарова, братан! Я Grok прямо в твоей Телеге 🔥\n"
        "Пиши что угодно — я всё помню, пока не нажмёшь кнопку снизу.",
        reply_markup=get_keyboard()
    )


@dp.message(F.text == "🧹 Очистить память")
async def clear_memory(message: Message):
    user_id = message.from_user.id
    history[user_id].clear()
    await message.answer("Память стёрта. Начинаем с чистого листа ✌️", reply_markup=get_keyboard())


@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = message.text

    # Добавляем сообщение юзера в историю
    history[user_id].append({"role": "user", "content": user_text})
    # Обрезаем историю до MAX_HISTORY сообщений
    if len(history[user_id]) > MAX_HISTORY:
        history[user_id] = history[user_id][-MAX_HISTORY:]

    await bot.send_chat_action(message.chat.id, "typing")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                GROK_URL,
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": history[user_id],
                    "temperature": 0.8,
                    "max_tokens": 3000
                },
                timeout=90.0
            )
            resp.raise_for_status()
            data = resp.json()
            grok_reply = data["choices"][0]["message"]["content"].strip()

            # Добавляем ответ Grok’а в историю
            history[user_id].append({"role": "assistant", "content": grok_reply})

            # Если слишком длинный — режем по 4096 символов
            if len(grok_reply) > 4096:
                for i in range(0, len(grok_reply), 4096):
                    await message.answer(grok_reply[i:i+4096])
            else:
                await message.answer(grok_reply, reply_markup=get_keyboard())

        except Exception as e:
            await message.answer(f"Грок словил ошибку 😵\n{e}\n\nПопробуй ещё разок через секунду спустя.",
                                 reply_markup=get_keyboard())


async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен и ждёт сообщений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())