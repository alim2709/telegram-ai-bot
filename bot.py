import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from openai import AsyncOpenAI

from repository import get_all_candles, get_candles_by_tag

load_dotenv()

logging.basicConfig(level=logging.INFO)

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY2"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://t.me/scenty_bot",
        "X-Title": "Scenty Aroma Assistant",
    },
)


BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)


def get_main_menu():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text="🧘 Под настроение"),
                KeyboardButton(text="🎁 На подарок"),
            ],
            [
                KeyboardButton(text="📦 Посмотреть каталог"),
                KeyboardButton(text="❓ Частые вопросы"),
            ],
        ],
    )


def get_mood_menu():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text="Устал(а), хочу расслабиться"),
                KeyboardButton(text="Хочется уюта и тепла"),
            ],
            [
                KeyboardButton(text="В поиске вдохновения"),
                KeyboardButton(text="Хочу романтики"),
            ],
            [
                KeyboardButton(text="Просто хочу что-то красивое"),
                KeyboardButton(text="⬅️ Назад"),
            ],
        ],
    )


def get_gift_menu():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="Подруга"), KeyboardButton(text="Мама")],
            [KeyboardButton(text="Коллега"), KeyboardButton(text="Себе 🎁")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
    )


@router.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Привет! Я Scenty — твой ароматный помощник ✨\n"
        "Помогу выбрать свечу под настроение или на подарок.\n\n"
        "С чего начнём?",
        reply_markup=get_main_menu(),
    )


@router.message(lambda msg: msg.text == "🧘 Под настроение")
async def mood_handler(message: types.Message):
    await message.answer(
        "Как ты себя сегодня чувствуешь?", reply_markup=get_mood_menu()
    )


@router.message(
    lambda msg: msg.text
    in [
        "Устал(а), хочу расслабиться",
        "Хочется уюта и тепла",
        "В поиске вдохновения",
        "Хочу романтики",
        "Просто хочу что-то красивое",
    ]
)
async def mood_result(message: types.Message):
    mood_to_tag = {
        "Устал(а), хочу расслабиться": "релакс",
        "Хочется уюта и тепла": "уют",
        "В поиске вдохновения": "вдохновение",
        "Хочу романтики": "романтика",
        "Просто хочу что-то красивое": "красота",
    }
    tag = mood_to_tag.get(message.text)
    reply = await recommend_by_tag(message.text, tag)
    await message.answer(reply)


@router.message(lambda msg: msg.text == "🎁 На подарок")
async def gift_handler(message: types.Message):
    await message.answer("Для кого выбираем подарок?", reply_markup=get_gift_menu())


@router.message(lambda msg: msg.text in ["Подруга", "Мама", "Коллега", "Себе 🎁"])
async def gift_result(message: types.Message):
    gift_to_tag = {
        "Подруга": "подруга",
        "Мама": "мама",
        "Коллега": "коллега",
        "Себе 🎁": "универсальный",
    }
    tag = gift_to_tag.get(message.text)
    reply = await recommend_by_tag(message.text, tag)
    await message.answer(reply)


@router.message(lambda msg: msg.text == "📦 Посмотреть каталог")
async def catalog_handler(message: types.Message):
    await message.answer(
        "Вот наш каталог: https://example.com/catalog\nСкоро будет больше новинок!"
    )


@router.message(lambda msg: msg.text == "❓ Частые вопросы")
async def faq_handler(message: types.Message):
    await message.answer(
        "📌 Частые вопросы:\n"
        "1. Состав — только натуральный воск, без парафина.\n"
        "2. Доставка — по всей Европе.\n"
        "3. Оплата — картой или PayPal.\n"
        "4. Возвраты — в течение 14 дней."
    )


@router.message(lambda msg: msg.text == "⬅️ Назад")
async def back_handler(message: types.Message):
    await message.answer("С чего начнём?", reply_markup=get_main_menu())


@router.message()
async def handle_ai_query(message: types.Message):
    user_msg = message.text
    reply = await get_aroma_recommendation(user_msg)
    await message.answer(reply)


async def build_prompt_by_tag(tag: str, user_message: str) -> str:
    candles = await get_candles_by_tag(tag)
    if not candles:
        return f"В каталоге пока нет подходящих свечей для {tag} 😔"

    prompt = "Вот свечи из каталога, которые подходят по описанию:\n"
    for c in candles:
        prompt += f"- {c.title} — {c.notes}. {c.description or ''}\n"

    full_prompt = (
        f"{prompt}\n\n"
        f"Пользователь: {user_message}\n\n"
        "Выбери из этого списка 1 свечу, которая лучше всего подойдёт. "
        "Ответь красиво, коротко (до 2 предложений), с упоминанием названия свечи и атмосферы, которую она создаёт."
    )
    return full_prompt


async def build_catalog_prompt():
    candles = await get_all_candles()
    if not candles:
        return "Каталог временно пуст. Мы работаем над ароматами ✨"

    prompt = "Вот наш каталог ароматных свечей:\n"
    for candle in candles:
        prompt += f"- {candle.title} — {candle.notes}. {candle.description or ''}\n"
    return prompt


async def recommend_by_tag(user_message: str, tag: str) -> str:
    try:
        prompt = await build_prompt_by_tag(tag, user_message)
        response = await client.chat.completions.create(
            model="openai/gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Ты ароматный помощник. Отвечай стильно, кратко и по сути.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[AI ERROR]: {e}")
        return "Пока не могу подобрать свечу, но скоро всё исправим 🌙"


async def get_aroma_recommendation(user_message: str) -> str:
    try:
        catalog_prompt = await build_catalog_prompt()

        response = await client.chat.completions.create(
            model="openai/gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты стильный и дружелюбный ароматный помощник. "
                        "Твоя задача — рекомендовать свечу из каталога, ориентируясь на настроение пользователя. "
                        "Говори коротко, красиво и по делу. Не объясняй, не повторяй весь каталог. "
                        "Ответ — не более 2 предложений. Упомяни название свечи и атмосферу, которую она создаёт."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{catalog_prompt}\n\nПользователь: {user_message}",
                },
            ],
            temperature=0.85,
            max_tokens=200,
        )

        if (
            response.choices
            and response.choices[0].message
            and response.choices[0].message.content
        ):
            return response.choices[0].message.content.strip()
        else:
            print(f"[AI WARNING]: Empty response content: {response}")
            return "Пока не могу подобрать аромат — попробуй чуть позже 🌙"
    except Exception as e:
        print(f"[AI ERROR]: {e}")
        return "Сегодня аромат в пути, но я обязательно подберу его для тебя позже 🌙"


# Launch bot
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
