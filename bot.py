import logging
import json
import os
import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_USERNAME = "petiko"  # твой username без @
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ── STATES ────────────────────────────────────────────────────────────────────
class Survey(StatesGroup):
    q1  = State(); q2  = State(); q3  = State(); q4  = State()
    q5  = State(); q6  = State(); q7  = State(); q8  = State()
    q9  = State(); q10 = State(); q11 = State(); q12 = State()
    q13 = State(); q14 = State(); q15 = State(); q16 = State()
    q17 = State()

STATES = [
    Survey.q1,  Survey.q2,  Survey.q3,  Survey.q4,  Survey.q5,
    Survey.q6,  Survey.q7,  Survey.q8,  Survey.q9,  Survey.q10,
    Survey.q11, Survey.q12, Survey.q13, Survey.q14, Survey.q15,
    Survey.q16, Survey.q17,
]

TOTAL = 17

# ── QUESTIONS ─────────────────────────────────────────────────────────────────
QUESTIONS = [
    {
        "key": "age",
        "text": "Сколько тебе сейчас лет?",
        "keys": None,
    },
    {
        "key": "school",
        "text": "В каком классе ты учишься?",
        "keys": None,
    },
    {
        "key": "daily_life",
        "text": "Опиши свой обычный день — что ты делаешь утром, днём и вечером?",
        "keys": None,
    },
    {
        "key": "interests",
        "text": "Назови несколько своих увлечений — то, что вызывает у тебя интерес и чем ты любишь заниматься в свободное время.",
        "keys": None,
    },
    {
        "key": "content",
        "text": "Какие мультики, фильмы, аниме или сериалы ты сейчас смотришь?",
        "keys": None,
    },
    {
        "key": "games",
        "text": "В какие игры играешь?\n_(если не играешь — так и напиши)_",
        "keys": None,
    },
    {
        "key": "music",
        "text": "Какую музыку любишь слушать? Есть ли любимые исполнители или жанры?",
        "keys": None,
    },
    {
        "key": "learning_style",
        "text": "Когда что-то непонятно — как ты обычно разбираешься?",
        "keys": [
            ["Гуглю сам(а)", "Спрашиваю у людей"],
            ["Смотрю YouTube", "Пробую методом тыка"],
            ["Прошу объяснить пошагово", "Бросаю и иду дальше"],
        ],
    },
    {
        "key": "motivation",
        "text": "Что тебе интереснее всего в учёбе?",
        "keys": [
            ["Когда сразу виден результат"],
            ["Когда это связано с реальной жизнью"],
            ["Когда есть соревнование или вызов"],
            ["Когда можно делать что-то руками"],
            ["Когда понятно, зачем это нужно"],
        ],
    },
    {
        "key": "want_to_learn",
        "text": "Что бы ты хотела уметь делать через год — то, чего не умеешь сейчас?\n\nМожешь написать любые навыки, желательно реалистичные.",
        "keys": None,
    },
    {
        "key": "device_usage",
        "text": "Как ты чаще всего используешь телефон?",
        "keys": [
            ["Соцсети и общение"],
            ["Смотрю видео / стримы"],
            ["Играю в игры"],
            ["Снимаю и монтирую"],
            ["Рисую / создаю контент"],
            ["Учусь онлайн"],
            ["По-разному, напишу сам(а)..."],
        ],
    },
    {
        "key": "ai_experience",
        "text": "Знакома ли ты с нейросетями? Есть ли у тебя какой-то опыт с ними?",
        "keys": [
            ["Нет, никогда не пробовала"],
            ["Слышала, но не пробовала"],
            ["Пробовала пару раз"],
            ["Да, использую иногда"],
            ["Использую регулярно"],
        ],
    },
    {
        "key": "self_description",
        "text": "Опиши себя тремя словами — выбери из вариантов или напиши своё:",
        "keys": [
            ["Творческая", "Общительная", "Спокойная"],
            ["Любопытная", "Упрямая", "Весёлая"],
            ["Серьёзная", "Мечтательная", "Энергичная"],
            ["Напишу своё..."],
        ],
    },
    {
        "key": "proud_of",
        "text": "Что у тебя хорошо получается?\n\nВыбери или напиши своё:",
        "keys": [
            ["Рисую / создаю"],
            ["Хорошо учусь"],
            ["Умею дружить"],
            ["Разбираюсь в технологиях"],
            ["Занимаюсь спортом"],
            ["Хорошо объясняю другим"],
            ["Напишу своё..."],
        ],
    },
    {
        "key": "annoys",
        "text": "Что тебя больше всего раздражает — в учёбе, в людях или в жизни?\n\nВыбери или напиши своё:",
        "keys": [
            ["Скука и однообразие"],
            ["Когда не объясняют зачем"],
            ["Медленный темп"],
            ["Когда не слушают"],
            ["Много теории без практики"],
            ["Напишу своё..."],
        ],
    },
    {
        "key": "ai_dream",
        "text": "Если бы у тебя был личный помощник — какие задачи бы он выполнял за тебя, которые тебе не нравится делать?",
        "keys": None,
    },
    {
        "key": "life_goal",
        "text": "И последний вопрос 🙂\n\nКакая у тебя сейчас цель в жизни?",
        "keys": None,
    },
]

KEYS = [q["key"] for q in QUESTIONS]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def make_kb(rows):
    if not rows:
        return ReplyKeyboardRemove()
    buttons = [[KeyboardButton(text=t) for t in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def progress(step):
    filled = round(step / TOTAL * 10)
    return "▓" * filled + "░" * (10 - filled) + f" {step}/{TOTAL}"

def get_user_name(state_data):
    return state_data.get("user_first_name", "")

def build_profile(answers: dict, user_info: dict) -> str:
    name = user_info.get("first_name", "—")
    username = user_info.get("username", "—")
    user_id = user_info.get("id", "—")

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🧠 Профиль: {name} (@{username})",
        f"Telegram ID: {user_id}",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
        f"🎂 Возраст: {answers.get('age','—')}",
        f"🏫 Класс: {answers.get('school','—')}",
        f"☀️ Обычный день: {answers.get('daily_life','—')}\n",
        "── ИНТЕРЕСЫ ──",
        f"⭐ Увлечения: {answers.get('interests','—')}",
        f"📺 Контент: {answers.get('content','—')}",
        f"🎮 Игры: {answers.get('games','—')}",
        f"🎵 Музыка: {answers.get('music','—')}\n",
        "── КАК ДУМАЕТ ──",
        f"🔍 Стиль обучения: {answers.get('learning_style','—')}",
        f"💡 Что цепляет: {answers.get('motivation','—')}",
        f"🎯 Хочет уметь: {answers.get('want_to_learn','—')}\n",
        "── ТЕХНОЛОГИИ ──",
        f"📱 Телефон: {answers.get('device_usage','—')}",
        f"🤖 Опыт с AI: {answers.get('ai_experience','—')}\n",
        "── ЛИЧНОЕ ──",
        f"🪞 3 слова: {answers.get('self_description','—')}",
        f"🏆 Что получается: {answers.get('proud_of','—')}",
        f"😤 Раздражает: {answers.get('annoys','—')}",
        f"🤝 Помощник бы делал: {answers.get('ai_dream','—')}",
        f"🌟 Цель в жизни: {answers.get('life_goal','—')}\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)

def build_json(answers: dict, user_info: dict) -> str:
    name = user_info.get("first_name", "Пользователь")
    age = answers.get("age", "")
    age_num = re.search(r'\d+', age)

    interests_raw = answers.get("interests", "")
    interests = [i.strip() for i in re.split(r'[,;/\n]', interests_raw) if i.strip()][:6]

    profile = {
        "name": name,
        "age": age_num.group() if age_num else age,
        "gender": "девочка",
        "interests": interests,
        "favorites": f"{answers.get('content','')} | {answers.get('games','')} | {answers.get('music','')}",
        "techLevel": answers.get("ai_experience", ""),
        "learningStyle": answers.get("learning_style", ""),
        "motivation": answers.get("motivation", ""),
        "goal": answers.get("life_goal", ""),
        "wantToLearn": answers.get("want_to_learn", ""),
        "selfDescription": answers.get("self_description", ""),
        "strengths": answers.get("proud_of", ""),
        "painPoints": answers.get("annoys", ""),
        "delegateTasks": answers.get("ai_dream", ""),
        "deviceUsage": answers.get("device_usage", ""),
        "dailyLife": answers.get("daily_life", ""),
    }
    return json.dumps(profile, ensure_ascii=False, indent=2)

# ── HANDLERS ──────────────────────────────────────────────────────────────────
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    first_name = message.from_user.first_name or "друг"
    await state.update_data(
        answers={},
        user_info={
            "first_name": first_name,
            "username": message.from_user.username or "",
            "id": message.from_user.id,
        }
    )

    intro = (
        f"Привет, {first_name}! 👋\n\n"
        "Я хочу задать тебе несколько вопросов — это займёт минут 5–10.\n\n"
        "Отвечай честно — тут нет правильных или неправильных ответов. "
        "Так я узнаю о тебе чуть больше: чем ты живёшь, чем увлекаешься и что тебе интересно.\n\n"
        "Готова? Тогда начнём 🙂"
    )
    await message.answer(intro, reply_markup=ReplyKeyboardRemove())

    # Send first question
    q = QUESTIONS[0]
    await message.answer(
        f"*Вопрос 1/{TOTAL}*\n{q['text']}\n\n`{progress(1)}`",
        parse_mode="Markdown",
        reply_markup=make_kb(q["keys"])
    )
    await state.set_state(Survey.q1)

async def handle_q(message: Message, state: FSMContext, step: int):
    data = await state.get_data()
    answers = data.get("answers", {})
    answers[KEYS[step - 1]] = message.text.strip()
    await state.update_data(answers=answers)

    if step < TOTAL:
        q = QUESTIONS[step]
        await message.answer(
            f"*Вопрос {step + 1}/{TOTAL}*\n{q['text']}\n\n`{progress(step + 1)}`",
            parse_mode="Markdown",
            reply_markup=make_kb(q["keys"])
        )
        await state.set_state(STATES[step])
    else:
        user_info = data.get("user_info", {})
        await finish(message, answers, user_info)
        await state.clear()

async def finish(message: Message, answers: dict, user_info: dict):
    first_name = user_info.get("first_name", "")

    # Thank user
    await message.answer(
        f"Спасибо, {first_name}! 🙏\n\n"
        "Ты отлично справилась — ответила на все вопросы.\n"
        "Я уже передал твои ответы — скоро всё будет готово 🔥",
        reply_markup=ReplyKeyboardRemove()
    )

    # Send to admin
    if ADMIN_ID:
        bot = message.bot
        profile_text = build_profile(answers, user_info)
        json_str = build_json(answers, user_info)

        await bot.send_message(
            ADMIN_ID,
            f"📥 Новый профиль заполнен\n\n{profile_text}",
        )
        await bot.send_message(
            ADMIN_ID,
            f"```json\n{json_str}\n```",
            parse_mode="Markdown"
        )

# ── REGISTER STEP HANDLERS ────────────────────────────────────────────────────
def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_start, Command("restart"))

    async def make_handler(step):
        async def handler(message: Message, state: FSMContext):
            await handle_q(message, state, step)
        return handler

    loop = asyncio.new_event_loop()
    for i, st in enumerate(STATES):
        step = i + 1
        handler = loop.run_until_complete(make_handler(step))
        dp.message.register(handler, st, F.text)
    loop.close()

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_start, Command("restart"))

    for i, st in enumerate(STATES):
        step = i + 1

        def make_handler(s):
            async def handler(message: Message, state: FSMContext):
                await handle_q(message, state, s)
            return handler

        dp.message.register(make_handler(step), st, F.text)

    logger.info(f"Bot started. ADMIN_ID={ADMIN_ID}")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
