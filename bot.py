import asyncio
import html
import json
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

QUESTIONS: list[dict] = [
    {
        "id": 1,
        "text": "Как тебя <b>зовут</b> и сколько тебе <b>лет</b>?",
        "type": "text",
        "key": "name_age",
    },
    {
        "id": 2,
        "text": "📚 В каком ты <b>классе / на каком курсе</b>? Или чем занимаешься?",
        "type": "text",
        "key": "class_or_occupation",
    },
    {
        "id": 3,
        "text": "🌅 Опиши свой <b>обычный день</b> — что делаешь с утра до вечера?",
        "type": "text",
        "key": "typical_day",
    },
    {
        "id": 4,
        "text": "⭐ Назови <b>3–5 увлечений</b> — чем любишь заниматься в свободное время?",
        "type": "text",
        "key": "hobbies",
    },
    {
        "id": 5,
        "text": "🎬 Какие <b>сериалы, аниме или фильмы</b> сейчас смотришь или любишь?",
        "type": "text",
        "key": "media_favorites",
    },
    {
        "id": 6,
        "text": "🎮 В какие <b>игры</b> играешь? Если не играешь — напиши «не играю».",
        "type": "text",
        "key": "games",
    },
    {
        "id": 7,
        "text": "🎵 Какую <b>музыку</b> слушаешь? Любимые исполнители или жанры?",
        "type": "text",
        "key": "music",
    },
    {
        "id": 8,
        "text": "🔍 Когда что-то <b>непонятно</b> — как обычно разбираешься?",
        "type": "buttons",
        "key": "learning_method",
        "options": [
            "🔎 Гуглю сам(а)",
            "💬 Спрашиваю друзей",
            "👨‍🏫 Иду к учителю / родителям",
            "📺 Смотрю YouTube",
            "🎲 Пробую методом тыка",
        ],
    },
    {
        "id": 9,
        "text": "✨ Что <b>цепляет</b> тебя в учёбе — когда становится по-настоящему интересно?",
        "type": "buttons",
        "key": "study_engagement",
        "options": [
            "🛠 Практические задачи",
            "💡 Интересная теория",
            "🏆 Соревнования / рейтинги",
            "🎨 Творческие задания",
            "😐 Пока ничего не цепляет",
        ],
    },
    {
        "id": 10,
        "text": "⏱ <b>Сколько времени</b> готов(а) тратить на одно задание?",
        "type": "buttons",
        "key": "session_time",
        "options": [
            "⚡ До 15 минут",
            "🕐 15–30 минут",
            "🕑 30–60 минут",
            "🕒 Больше часа",
            "🎲 Зависит от настроения",
        ],
    },
    {
        "id": 11,
        "text": "🚀 Что хочешь <b>уметь делать</b> через год? Любые навыки!",
        "type": "text",
        "key": "skills_goal",
    },
    {
        "id": 12,
        "text": "📱 Как чаще всего <b>используешь телефон</b>?",
        "type": "buttons",
        "key": "phone_usage",
        "options": [
            "💬 Соцсети и общение",
            "🎮 Игры",
            "📖 Учёба и саморазвитие",
            "🎬 Видео / музыка / развлечения",
            "🔀 Всё понемногу",
        ],
    },
    {
        "id": 13,
        "text": "🤖 Каков твой <b>опыт с AI</b> (ChatGPT, Midjourney и т.д.)?",
        "type": "buttons",
        "key": "ai_experience",
        "options": [
            "❌ Никогда не пробовал(а)",
            "👂 Слышал(а), но не использовал(а)",
            "📚 Иногда использую для учёбы",
            "🔄 Регулярно использую",
            "💪 Использую каждый день",
        ],
    },
    {
        "id": 14,
        "text": "💭 Какие у тебя <b>мысли об AI</b>? Это хорошо или плохо — и почему?",
        "type": "text",
        "key": "ai_thoughts",
    },
    {
        "id": 15,
        "text": "🪞 Опиши себя <b>тремя словами</b>:",
        "type": "text",
        "key": "self_description",
    },
    {
        "id": 16,
        "text": "🏅 Чем ты <b>гордишься</b> — в себе, делах или достижениях?",
        "type": "text",
        "key": "proud_of",
    },
    {
        "id": 17,
        "text": "😤 Что тебя <b>раздражает</b> — в учёбе, людях или технологиях?",
        "type": "text",
        "key": "pain_points",
    },
    {
        "id": 18,
        "text": "✨ Если бы у тебя был идеальный <b>AI-помощник</b> — что бы он делал для тебя?",
        "type": "text",
        "key": "ai_dream",
    },
    {
        "id": 19,
        "text": (
            "❓ Есть что-то, в чём <b>хочешь разобраться</b>, "
            "но пока не знаешь с чего начать?\n\n"
            "<i>Можешь пропустить этот вопрос.</i>"
        ),
        "type": "text_with_skip",
        "key": "want_to_learn",
        "skip_label": "⏭ Пропустить",
    },
    {
        "id": 20,
        "text": "🎯 Последний вопрос! Какова твоя <b>главная цель</b> на этом курсе?",
        "type": "text",
        "key": "course_goal",
    },
]


class Survey(StatesGroup):
    answering = State()


def progress_bar(current: int, total: int = 20) -> str:
    filled = round(current * 10 / total)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"{bar} {current}/{total}"


def buttons_keyboard(options: list[str], q_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=opt, callback_data=f"ans_{q_id}_{i}")]
        for i, opt in enumerate(options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_keyboard(q_id: int, label: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"skip_{q_id}")]]
    )


async def send_question(chat_id: int, q: dict) -> None:
    header = f"<code>{progress_bar(q['id'])}</code>\n\n"
    text = header + q["text"]
    kwargs: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    if q["type"] == "buttons":
        kwargs["reply_markup"] = buttons_keyboard(q["options"], q["id"])
    elif q["type"] == "text_with_skip":
        kwargs["reply_markup"] = skip_keyboard(q["id"], q.get("skip_label", "Пропустить"))

    await bot.send_message(**kwargs)


async def advance(chat_id: int, state: FSMContext, answer: str) -> None:
    data = await state.get_data()
    idx: int = data.get("current_q", 0)
    answers: dict = data.get("answers", {})
    q = QUESTIONS[idx]

    answers[q["key"]] = answer
    next_idx = idx + 1
    await state.update_data(current_q=next_idx, answers=answers)

    if next_idx >= len(QUESTIONS):
        await finish_survey(chat_id, answers, state)
    else:
        await send_question(chat_id, QUESTIONS[next_idx])


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Survey.answering)
    await state.update_data(current_q=0, answers={})

    await message.answer(
        "🤖 <b>Привет! Давай знакомиться.</b>\n\n"
        "Я задам тебе 20 вопросов — займёт около 5–10 минут.\n"
        "Отвечай честно, нет правильных или неправильных ответов.\n\n"
        "Поехали! 🚀",
        parse_mode="HTML",
    )
    await send_question(message.chat.id, QUESTIONS[0])


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нечего отменять. Напиши /start чтобы начать анкету.")
        return
    await state.clear()
    await message.answer("❌ Анкета отменена. Напиши /start чтобы начать заново.")


@dp.message(Survey.answering)
async def handle_text(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пожалуйста, отправь текстовое сообщение.")
        return

    data = await state.get_data()
    idx: int = data.get("current_q", 0)
    q = QUESTIONS[idx]

    if q["type"] == "buttons":
        await message.answer("👆 Пожалуйста, выбери один из вариантов выше.")
        return

    await advance(message.chat.id, state, message.text.strip())


@dp.callback_query(Survey.answering, F.data.startswith("ans_"))
async def handle_button(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    idx: int = data.get("current_q", 0)
    q = QUESTIONS[idx]

    # callback_data format: ans_{q_id}_{opt_index}
    parts = callback.data.split("_")
    q_id = int(parts[1])
    opt_idx = int(parts[2])

    if q["id"] != q_id:
        await callback.answer("Это кнопка от предыдущего вопроса.", show_alert=True)
        return

    chosen = q["options"][opt_idx]
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ <b>{html.escape(chosen)}</b>", parse_mode="HTML"
    )
    await advance(callback.message.chat.id, state, chosen)


@dp.callback_query(Survey.answering, F.data.startswith("skip_"))
async def handle_skip(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    idx: int = data.get("current_q", 0)
    q = QUESTIONS[idx]

    # callback_data format: skip_{q_id}
    q_id = int(callback.data.split("_")[1])

    if q["id"] != q_id:
        await callback.answer("Это кнопка от предыдущего вопроса.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("⏭ <i>Пропущено</i>", parse_mode="HTML")
    await advance(callback.message.chat.id, state, "—")


@dp.message()
async def fallback(message: Message) -> None:
    await message.answer("Напиши /start чтобы начать анкету 🚀")


def build_profile_html(answers: dict) -> str:
    def a(key: str) -> str:
        return html.escape(str(answers.get(key, "—")))

    return (
        "📋 <b>АНКЕТА УЧАСТНИКА</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Имя и возраст:</b> {a('name_age')}\n"
        f"📚 <b>Класс / курс:</b> {a('class_or_occupation')}\n"
        f"🌅 <b>Обычный день:</b> {a('typical_day')}\n\n"
        "⭐ <b>ИНТЕРЕСЫ</b>\n"
        f"• Увлечения: {a('hobbies')}\n"
        f"• Медиа: {a('media_favorites')}\n"
        f"• Игры: {a('games')}\n"
        f"• Музыка: {a('music')}\n\n"
        "🧠 <b>СТИЛЬ ОБУЧЕНИЯ</b>\n"
        f"• Разбирается в непонятном: {a('learning_method')}\n"
        f"• Что цепляет в учёбе: {a('study_engagement')}\n"
        f"• Время на задание: {a('session_time')}\n"
        f"• Хочет уметь: {a('skills_goal')}\n\n"
        "📱 <b>ТЕХНОЛОГИИ И AI</b>\n"
        f"• Использование телефона: {a('phone_usage')}\n"
        f"• Опыт с AI: {a('ai_experience')}\n"
        f"• Мысли об AI: {a('ai_thoughts')}\n\n"
        "🪞 <b>ЛИЧНОСТЬ</b>\n"
        f"• 3 слова о себе: {a('self_description')}\n"
        f"• Чем гордится: {a('proud_of')}\n"
        f"• Что раздражает: {a('pain_points')}\n\n"
        "🎯 <b>ЦЕЛИ</b>\n"
        f"• Мечта с AI: {a('ai_dream')}\n"
        f"• Хочет разобраться: {a('want_to_learn')}\n"
        f"• Цель курса: {a('course_goal')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def build_json_profile(answers: dict) -> dict:
    return {
        "name": answers.get("name_age", ""),
        "age": "",
        "interests": [h.strip() for h in answers.get("hobbies", "").split(",") if h.strip()],
        "favorites": {
            "media": answers.get("media_favorites", ""),
            "games": answers.get("games", ""),
            "music": answers.get("music", ""),
        },
        "techLevel": answers.get("ai_experience", ""),
        "learningStyle": {
            "method": answers.get("learning_method", ""),
            "engagement": answers.get("study_engagement", ""),
        },
        "motivation": answers.get("course_goal", ""),
        "sessionTime": answers.get("session_time", ""),
        "goal": answers.get("course_goal", ""),
        "wantToLearn": answers.get("want_to_learn", ""),
        "selfDescription": answers.get("self_description", ""),
        "painPoints": answers.get("pain_points", ""),
        "aiDream": answers.get("ai_dream", ""),
    }


async def finish_survey(chat_id: int, answers: dict, state: FSMContext) -> None:
    await state.clear()

    await bot.send_message(
        chat_id,
        "🎉 <b>Отлично! Анкета заполнена!</b>\n\n"
        "Спасибо за честные ответы — это поможет сделать курс максимально полезным для тебя.\n"
        "Увидимся на курсе! 🚀",
        parse_mode="HTML",
    )

    try:
        await bot.send_message(ADMIN_ID, build_profile_html(answers), parse_mode="HTML")

        json_data = build_json_profile(answers)
        json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
        await bot.send_message(
            ADMIN_ID,
            f"<pre>{html.escape(json_str)}</pre>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Failed to notify admin: %s", e)


async def main() -> None:
    logger.info("Starting survey bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
