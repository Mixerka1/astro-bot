import asyncio
import hashlib
import logging
import os
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ ====================

# Токен берётся из переменной окружения BOT_TOKEN.
# В Railway: Project -> Variables -> добавить BOT_TOKEN = твой токен от BotFather.
# Для локального теста можно временно раскомментировать строку ниже и вписать токен напрямую:
# BOT_TOKEN = "123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxx"
BOT_TOKEN = os.environ["BOT_TOKEN"]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ==================== СОСТОЯНИЯ (FSM) ====================

class Form(StatesGroup):
    waiting_birthdate = State()
    waiting_name_1 = State()
    waiting_name_2 = State()


# ==================== ДАННЫЕ ДЛЯ ГЕНЕРАЦИИ ====================

ZODIAC_RANGES = [
    ((1, 20), (2, 18), "Водолей"),
    ((2, 19), (3, 20), "Рыбы"),
    ((3, 21), (4, 19), "Овен"),
    ((4, 20), (5, 20), "Телец"),
    ((5, 21), (6, 20), "Близнецы"),
    ((6, 21), (7, 22), "Рак"),
    ((7, 23), (8, 22), "Лев"),
    ((8, 23), (9, 22), "Дева"),
    ((9, 23), (10, 22), "Весы"),
    ((10, 23), (11, 21), "Скорпион"),
    ((11, 22), (12, 21), "Стрелец"),
    ((12, 22), (1, 19), "Козерог"),
]

TRAITS = [
    "сильная интуиция", "лидерские качества", "творческая энергия",
    "аналитический склад ума", "эмоциональная глубина", "магнетизм в общении",
    "тяга к независимости", "внутренняя гармония", "страсть к переменам",
    "умение слушать", "решительность", "чувство юмора",
]

DAILY_ADVICE = [
    "сегодня стоит довериться первому впечатлению",
    "хороший день для важного разговора",
    "звёзды советуют не спешить с решениями",
    "энергия дня благоволит новым знакомствам",
    "лучше отложить крупные траты",
    "самое время закрыть старый гештальт",
    "день располагает к творчеству",
    "стоит прислушаться к близкому человеку",
]

COMPAT_PHRASES_HIGH = [
    "редкое взаимное притяжение — такое совпадение встречается нечасто",
    "мощная химия и взаимное дополнение характеров",
    "гармония на всех уровнях: от бытового до эмоционального",
]

COMPAT_PHRASES_MID = [
    "есть потенциал, но потребуется работа над коммуникацией",
    "притяжение чувствуется, хотя характеры местами спорят",
    "интересный тандем с элементом непредсказуемости",
]

COMPAT_PHRASES_LOW = [
    "разные скорости в жизни, но противоположности иногда притягиваются",
    "потребуется терпение — слишком разные подходы к жизни",
    "сложное сочетание, но не безнадёжное",
]


def get_zodiac(day: int, month: int) -> str:
    for (start_m, start_d), (end_m, end_d), sign in ZODIAC_RANGES:
        if start_m == month and day >= start_d:
            return sign
        if end_m == month and day <= end_d:
            return sign
        if start_m > end_m:  # переход через год (Козерог)
            if month == start_m and day >= start_d:
                return sign
            if month == end_m and day <= end_d:
                return sign
    return "Козерог"


def seeded_random(seed_str: str) -> random.Random:
    """Детерминированный рандом на основе строки — один и тот же ввод даёт одинаковый результат."""
    h = hashlib.sha256(seed_str.encode()).hexdigest()
    return random.Random(int(h, 16))


def generate_daily_forecast(name: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    rnd = seeded_random(name.lower() + today)
    trait = rnd.choice(TRAITS)
    advice = rnd.choice(DAILY_ADVICE)
    percent = rnd.randint(60, 99)
    return (
        f"🔮 Прогноз на сегодня\n\n"
        f"Заряд дня: {percent}%\n"
        f"Ключевая черта дня: {trait}\n"
        f"Совет: {advice}"
    )


def generate_compatibility(name1: str, name2: str) -> tuple[str, int]:
    seed = "_".join(sorted([name1.lower(), name2.lower()]))
    rnd = seeded_random(seed)
    percent = rnd.randint(35, 99)

    if percent >= 80:
        phrase = rnd.choice(COMPAT_PHRASES_HIGH)
    elif percent >= 55:
        phrase = rnd.choice(COMPAT_PHRASES_MID)
    else:
        phrase = rnd.choice(COMPAT_PHRASES_LOW)

    return phrase, percent


def generate_full_compatibility(name1: str, name2: str, percent: int) -> str:
    """Расширенный платный/рекламный результат."""
    rnd = seeded_random(name1.lower() + name2.lower() + "full")
    aspects = {
        "Эмоции": rnd.randint(40, 99),
        "Общение": rnd.randint(40, 99),
        "Долгосрочность": rnd.randint(40, 99),
        "Страсть": rnd.randint(40, 99),
    }
    lines = [f"📊 Полный расклад совместимости {name1} и {name2}\n"]
    for aspect, val in aspects.items():
        bar = "▓" * (val // 10) + "░" * (10 - val // 10)
        lines.append(f"{aspect}: {bar} {val}%")
    lines.append(f"\nОбщий процент: {percent}%")
    return "\n".join(lines)


# ==================== КЛАВИАТУРЫ ====================

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Прогноз дня", callback_data="daily")],
        [InlineKeyboardButton(text="💞 Совместимость", callback_data="compat")],
    ])


def unlock_full_kb(payload: str) -> InlineKeyboardMarkup:
    """
    Кнопка разблокировки полного результата.
    Сюда позже подключается rewarded-реклама (Adsgram/Onclickads) или Telegram Stars.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Смотреть рекламу и открыть полный расклад",
                               callback_data=f"unlock_{payload}")],
        [InlineKeyboardButton(text="⭐ Открыть за Stars", callback_data=f"stars_{payload}")],
    ])


# ==================== ХЕНДЛЕРЫ ====================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я покажу твой прогноз дня и совместимость с кем угодно ✨\n\n"
        "Выбери, что интересует:",
        reply_markup=main_menu_kb(),
    )


@dp.callback_query(F.data == "daily")
async def cb_daily(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_birthdate)
    await callback.message.answer("Введи своё имя или ник (для расчёта прогноза):")
    await callback.answer()


@dp.message(Form.waiting_birthdate)
async def process_daily_name(message: Message, state: FSMContext):
    name = message.text.strip()
    forecast = generate_daily_forecast(name)
    await message.answer(forecast, reply_markup=main_menu_kb())
    await state.clear()


@dp.callback_query(F.data == "compat")
async def cb_compat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_name_1)
    await callback.message.answer("Введи своё имя или ник:")
    await callback.answer()


@dp.message(Form.waiting_name_1)
async def process_name_1(message: Message, state: FSMContext):
    await state.update_data(name1=message.text.strip())
    await state.set_state(Form.waiting_name_2)
    await message.answer("Теперь введи имя/ник второго человека:")


@dp.message(Form.waiting_name_2)
async def process_name_2(message: Message, state: FSMContext):
    data = await state.get_data()
    name1 = data["name1"]
    name2 = message.text.strip()

    phrase, percent = generate_compatibility(name1, name2)
    short_result = (
        f"💞 Совместимость {name1} и {name2}: {percent}%\n\n"
        f"{phrase.capitalize()}"
    )

    payload = f"{name1}|{name2}"
    await message.answer(short_result, reply_markup=unlock_full_kb(payload))
    await state.clear()


@dp.callback_query(F.data.startswith("unlock_"))
async def cb_unlock(callback: CallbackQuery):
    """
    Здесь должна быть интеграция с рекламной сетью (например, Adsgram SDK через WebApp,
    или Onclickads rewarded ad callback). Пока — прямой показ результата (заглушка).
    """
    payload = callback.data.replace("unlock_", "", 1)
    name1, name2 = payload.split("|")
    _, percent = generate_compatibility(name1, name2)
    full = generate_full_compatibility(name1, name2, percent)

    # TODO: перед отправкой результата — проверка, что пользователь досмотрел рекламу
    await callback.message.answer(full)
    await callback.answer()


@dp.callback_query(F.data.startswith("stars_"))
async def cb_stars(callback: CallbackQuery):
    """
    Здесь должна быть отправка инвойса Telegram Stars через bot.send_invoice
    с currency='XTR'. Пока — заглушка с пояснением.
    """
    await callback.message.answer(
        "Оплата через Telegram Stars будет подключена здесь "
        "(bot.send_invoice с currency='XTR')."
    )
    await callback.answer()


# ==================== ЗАПУСК ====================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
