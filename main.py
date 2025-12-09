import asyncio
import logging
import os
from typing import Optional

import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

logging.basicConfig(level=logging.INFO)


TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "7212975362:AAELLSXg8Z1zd9fbQqN3thVbIgnHyhmq_Hk",
)
LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    "chad-95ad4d8019e14f34a5afd87f366b51c2bbnwbxlf",
).strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_API_BASE = os.getenv(
    "LLM_API_BASE",
    "https://ask.chadgpt.ru/api/public",
)  # базовый URL сервиса ChadGPT

dp = Dispatcher()

_SYSTEM_PROMPT = """
Ты фитнес-тренер и нутриционист. Кратко собирай вводные (возраст, пол,
уровень активности, цель, ограничения по здоровью/еде, доступное
оборудование, дни в неделю). Формируй план:
- Разминка
- Основные упражнения (подходы/повторы/отдых)
- Кардио/функционал
- Растяжка
- Питание (белки/жиры/углеводы, пример дня)
Давай варианты прогрессии на 4–6 недель и предупреждения по безопасности.
Пиши дружелюбно и структурированно.
""".strip()


def _build_keyboard() -> types.ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Подобрать план")
    kb.button(text="Совет по питанию")
    kb.button(text="Вопрос про тренировку")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


async def ask_llm(user_text: str) -> str:
    if not LLM_API_KEY:
        return "Не задан API-ключ LLM (переменная окружения LLM_API_KEY)."

    url = f"{LLM_API_BASE.rstrip('/')}/{LLM_MODEL}"
    payload = {"message": user_text, "api_key": LLM_API_KEY}

    try:
        response = await asyncio.to_thread(
            requests.post,
            url,
            json=payload,
            timeout=30,
        )
        if response.status_code != 200:
            return f"Сервис LLM вернул код {response.status_code}"

        data = response.json()
        if data.get("is_success"):
            return str(data.get("response", "")).strip()
        return f"Ошибка LLM: {data.get('error_message', 'unknown error')}"
    except Exception as exc:  # noqa: BLE001
        logging.exception("LLM request failed")
        return f"Не получилось получить ответ от модели: {exc}"


@dp.message(CommandStart())
async def start_command(message: types.Message) -> None:
    await message.answer(
        "Привет! Я фитнес-бот на основе LLM.\n"
        "Опиши цель (похудеть/набрать/поддерживать), твой уровень активности, "
        "ограничения и доступное оборудование — подготовлю план.",
        reply_markup=_build_keyboard(),
    )


@dp.message(Command("help"))
async def help_command(message: types.Message) -> None:
    await message.answer(
        "Напиши свободным текстом или выбери кнопку:\n"
        "• Подобрать план — персональный план тренировок\n"
        "• Совет по питанию — рекомендации по рациону\n"
        "• Вопрос про тренировку — разберём технику или замену упражнений",
        reply_markup=_build_keyboard(),
    )


@dp.message(F.text.in_(["Подобрать план", "Совет по питанию", "Вопрос про тренировку"]))
async def quick_start(message: types.Message) -> None:
    prompts = {
        "Подобрать план": (
            "Мне нужен персональный план. Укажи возраст, пол, уровень активности, "
            "цель (похудение/набор/рельеф), ограничения, оборудование и дни в неделю."
        ),
        "Совет по питанию": (
            "Дай рекомендации по питанию с учётом калорийности и БЖУ. "
            "Укажи мои данные (возраст, вес, рост, цель)."
        ),
        "Вопрос про тренировку": (
            "Задай любой вопрос: техника, замены упражнений, как прогрессировать."
        ),
    }
    await message.answer(prompts.get(message.text, "Напиши подробнее 🙂"))


@dp.message(F.text)
async def handle_text(message: types.Message) -> None:
    await message.answer("Думаю над планом... ⏳")
    reply = await ask_llm(message.text)
    await message.answer(reply, parse_mode=ParseMode.HTML)


async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    bot = Bot(TELEGRAM_BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
