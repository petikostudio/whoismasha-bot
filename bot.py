import logging
import json
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "")
ADMIN_ID    = int(os.environ.get("ADMIN_ID", "0"))  # твой Telegram user_id

# ── CONVERSATION STATES ───────────────────────────────────────────────────────
(
    Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10,
    Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q19, Q20
) = range(20)

# ── QUESTIONS ────────────────────────────────────────────────────────────────
QUESTIONS = [
    {
        "key": "name_age",
        "section": "01 — Базовое",
        "text": "Привет! Меня зовут AI-Quest 👾\n\nЯ задам тебе 20 вопросов — и на их основе создам курс, заточенный именно под тебя.\n\nЗдесь нет правильных и неправильных ответов. Чем честнее — тем лучше.\n\n*Начнём?*\n\n*Вопрос 1/20*\nКак тебя зовут и сколько тебе лет?",
        "keyboard": None,
    },
    {
        "key": "school",
        "section": None,
        "text": "*Вопрос 2/20*\nВ каком ты классе / на каком курсе / чем занимаешься по жизни?",
        "keyboard": None,
    },
    {
        "key": "daily_life",
        "section": None,
        "text": "*Вопрос 3/20*\nКак ты проводишь обычный день после школы? Опиши честно 🙂\n\n_Например: сижу в телефоне, рисую, гуляю, смотрю видео..._",
        "keyboard": None,
    },
    {
        "key": "interests",
        "section": "02 — Интересы",
        "text": "*Вопрос 4/20*\nНазови 3–5 вещей, которыми ты реально увлекаешься.\n\nНе то что «нормально», а то что по-настоящему нравится 🔥",
        "keyboard": None,
    },
    {
        "key": "content",
        "section": None,
        "text": "*Вопрос 5/20*\nКакие сериалы, аниме, фильмы или видео ты сейчас смотришь или смотрел(а) недавно?",
        "keyboard": None,
    },
    {
        "key": "games",
        "section": None,
        "text": "*Вопрос 6/20*\nВ какие игры играешь?\n\n_Можно написать «не играю» — это тоже нормально_",
        "keyboard": None,
    },
    {
        "key": "music",
        "section": None,
        "text": "*Вопрос 7/20*\nКакую музыку слушаешь? Назови 2–3 исполнителя или жанра.",
        "keyboard": None,
    },
    {
        "key": "learning_style",
        "section": "03 — Как ты думаешь",
        "text": "*Вопрос 8/20*\nКогда тебе что-то непонятно — как ты предпочитаешь разбираться?\n\n_Выбери один или напиши свой вариант_",
        "keyboard": [
            ["Гуглю сам(а)", "Спрашиваю у людей"],
            ["Смотрю YouTube", "Пробую методом тыка"],
            ["Прошу объяснить пошагово", "Бросаю и иду дальше"],
            ["✍️ Свой вариант..."],
        ],
    },
    {
        "key": "motivation",
        "section": None,
        "text": "*Вопрос 9/20*\nЧто тебя больше цепляет в учёбе или изучении нового?",
        "keyboard": [
            ["Когда сразу виден результат"],
            ["Когда связано с реальной жизнью"],
            ["Соревнование или вызов"],
            ["Делать что-то руками"],
            ["Когда понятно зачем это нужно"],
            ["✍️ Свой вариант..."],
        ],
    },
    {
        "key": "session_time",
        "section": None,
        "text": "*Вопрос 10/20*\nСколько времени ты готов(а) тратить на одно задание, чтобы не было скучно?",
        "keyboard": [
            ["5 минут", "10–15 минут"],
            ["20–30 минут", "Зависит от настроения"],
        ],
    },
    {
        "key": "want_to_learn",
        "section": None,
        "text": "*Вопрос 11/20*\nЕсть ли что-то, что ты хочешь уметь делать, но пока не умеешь?\n\n_Рисовать, петь, зарабатывать, говорить по-английски — любая сфера_",
        "keyboard": None,
    },
    {
        "key": "device_usage",
        "section": "04 — Ты и технологии",
        "text": "*Вопрос 12/20*\nКак ты сейчас используешь телефон/компьютер?\n\n_Напиши всё что делаешь регулярно_",
        "keyboard": [
            ["Соцсети и мессенджеры"],
            ["Смотрю видео / стримы"],
            ["Играю в игры"],
            ["Снимаю / монтирую видео"],
            ["Рисую / создаю контент"],
            ["Учусь онлайн"],
            ["Пишу тексты / веду блог"],
            ["✍️ Написать подробнее..."],
        ],
    },
    {
        "key": "ai_experience",
        "section": None,
        "text": "*Вопрос 13/20*\nПробовал(а) ли ты уже что-то с AI? ChatGPT, нейросети для картинок, голосовые помощники?",
        "keyboard": [
            ["Нет, вообще не пробовал(а)"],
            ["Пару раз из любопытства"],
            ["Да, использую иногда"],
            ["Да, использую регулярно"],
        ],
    },
    {
        "key": "ai_thoughts",
        "section": None,
        "text": "*Вопрос 14/20*\nЧто ты делал(а) с AI и что думаешь об этом?\n\n_Если не пробовал(а) — напиши что слышал(а) или думаешь об этом_",
        "keyboard": None,
    },
    {
        "key": "self_description",
        "section": "05 — Личное",
        "text": "*Вопрос 15/20*\nОпиши себя тремя словами — как бы ты сам(а) себя охарактеризовал(а)?",
        "keyboard": None,
    },
    {
        "key": "proud_of",
        "section": None,
        "text": "*Вопрос 16/20*\nЧем ты гордишься? Что у тебя получается хорошо — даже если кажется мелочью? 🌟",
        "keyboard": None,
    },
    {
        "key": "annoys",
        "section": None,
        "text": "*Вопрос 17/20*\nЧто тебя раздражает или бесит больше всего — в учёбе, в людях, в мире?\n\n_Честно. Это поможет избежать похожего в курсе_",
        "keyboard": None,
    },
    {
        "key": "ai_dream",
        "section": None,
        "text": "*Вопрос 18/20*\nЕсли бы ты прямо сейчас мог(ла) научиться чему-то одному с помощью AI — что бы это было?",
        "keyboard": None,
    },
    {
        "key": "secret_topic",
        "section": None,
        "text": "*Вопрос 19/20* _(необязательный)_\nЕсть что-то, о чём ты давно хочешь поговорить или разобраться, но не с кем / некогда / неловко?\n\n_Можно пропустить — напиши «пропустить»_",
        "keyboard": [["Пропустить"]],
    },
    {
        "key": "course_goal",
        "section": None,
        "text": "*Вопрос 20/20* — последний! 🎉\nНапиши одно — самое важное — чего ты хочешь от этого курса.\n\nОдним предложением.",
        "keyboard": None,
    },
]

KEYS = [q["key"] for q in QUESTIONS]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def make_keyboard(options):
    if not options:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(options, resize_keyboard=True, one_time_keyboard=True)

def progress_bar(step, total=20):
    filled = round(step / total * 10)
    return "▓" * filled + "░" * (10 - filled) + f" {step}/{total}"

async def send_question(update: Update, state: int, context: ContextTypes.DEFAULT_TYPE):
    q = QUESTIONS[state]
    text = q["text"]
    kb = make_keyboard(q["keyboard"])
    bar = f"\n\n`{progress_bar(state + 1)}`"
    await update.message.reply_text(
        text + bar,
        parse_mode="Markdown",
        reply_markup=kb
    )

def build_profile(answers: dict) -> str:
    """Форматирует ответы в структурированный профиль."""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "🧠 *ПРОФИЛЬ AI-QUEST*",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
        f"👤 *Кто:* {answers.get('name_age', '—')}",
        f"🏫 *Учёба:* {answers.get('school', '—')}",
        f"☀️ *Обычный день:* {answers.get('daily_life', '—')}\n",
        "─── ИНТЕРЕСЫ ───",
        f"⭐ *Увлечения:* {answers.get('interests', '—')}",
        f"📺 *Контент:* {answers.get('content', '—')}",
        f"🎮 *Игры:* {answers.get('games', '—')}",
        f"🎵 *Музыка:* {answers.get('music', '—')}\n",
        "─── КАК ДУМАЕТ ───",
        f"🔍 *Стиль обучения:* {answers.get('learning_style', '—')}",
        f"💡 *Что цепляет:* {answers.get('motivation', '—')}",
        f"⏱ *Время на задание:* {answers.get('session_time', '—')}",
        f"🎯 *Хочет уметь:* {answers.get('want_to_learn', '—')}\n",
        "─── ТЕХНОЛОГИИ ───",
        f"📱 *Использование:* {answers.get('device_usage', '—')}",
        f"🤖 *Опыт с AI:* {answers.get('ai_experience', '—')}",
        f"💭 *Мысли об AI:* {answers.get('ai_thoughts', '—')}\n",
        "─── ЛИЧНОЕ ───",
        f"🪞 *3 слова о себе:* {answers.get('self_description', '—')}",
        f"🏆 *Гордится:* {answers.get('proud_of', '—')}",
        f"😤 *Раздражает:* {answers.get('annoys', '—')}",
        f"✨ *Мечта с AI:* {answers.get('ai_dream', '—')}",
        f"🤫 *Хочет разобраться:* {answers.get('secret_topic', '—')}",
        f"🎯 *Цель курса:* {answers.get('course_goal', '—')}\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)

def build_json(answers: dict) -> str:
    """JSON для вставки в AI-Quest приложение."""
    name_age = answers.get("name_age", "")
    # Try to extract name
    name = name_age.split(",")[0].split(" ")[0] if name_age else "Пользователь"
    # Try to extract age
    import re
    age_match = re.search(r'\d+', name_age)
    age = age_match.group() if age_match else "13"

    interests_raw = answers.get("interests", "")
    interests = [i.strip() for i in re.split(r'[,;/\n]', interests_raw) if i.strip()][:6]

    profile = {
        "name": name,
        "age": age,
        "gender": "не указан",
        "interests": interests,
        "favorites": f"{answers.get('content', '')} | {answers.get('games', '')} | {answers.get('music', '')}",
        "techLevel": answers.get("ai_experience", "новичок"),
        "learningStyle": answers.get("learning_style", ""),
        "motivation": answers.get("motivation", ""),
        "sessionTime": answers.get("session_time", ""),
        "goal": answers.get("course_goal", ""),
        "wantToLearn": answers.get("want_to_learn", ""),
        "selfDescription": answers.get("self_description", ""),
        "painPoints": answers.get("annoys", ""),
        "aiDream": answers.get("ai_dream", ""),
        "rawAnswers": answers,
    }
    return json.dumps(profile, ensure_ascii=False, indent=2)

# ── HANDLERS ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["answers"] = {}
    await send_question(update, 0, context)
    return Q1

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, state: int):
    answer = update.message.text.strip()
    key = KEYS[state]

    # Skip handling for optional question
    if answer == "Пропустить":
        answer = "—"

    context.user_data["answers"][key] = answer
    next_state = state + 1

    if next_state < len(QUESTIONS):
        await send_question(update, next_state, context)
        return next_state
    else:
        await finish(update, context)
        return ConversationHandler.END

# Generate handlers for each state
async def h1(u, c): return await handle_answer(u, c, 0)
async def h2(u, c): return await handle_answer(u, c, 1)
async def h3(u, c): return await handle_answer(u, c, 2)
async def h4(u, c): return await handle_answer(u, c, 3)
async def h5(u, c): return await handle_answer(u, c, 4)
async def h6(u, c): return await handle_answer(u, c, 5)
async def h7(u, c): return await handle_answer(u, c, 6)
async def h8(u, c): return await handle_answer(u, c, 7)
async def h9(u, c): return await handle_answer(u, c, 8)
async def h10(u, c): return await handle_answer(u, c, 9)
async def h11(u, c): return await handle_answer(u, c, 10)
async def h12(u, c): return await handle_answer(u, c, 11)
async def h13(u, c): return await handle_answer(u, c, 12)
async def h14(u, c): return await handle_answer(u, c, 13)
async def h15(u, c): return await handle_answer(u, c, 14)
async def h16(u, c): return await handle_answer(u, c, 15)
async def h17(u, c): return await handle_answer(u, c, 16)
async def h18(u, c): return await handle_answer(u, c, 17)
async def h19(u, c): return await handle_answer(u, c, 18)
async def h20(u, c): return await handle_answer(u, c, 19)

HANDLERS = [h1,h2,h3,h4,h5,h6,h7,h8,h9,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20]

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answers = context.user_data.get("answers", {})
    user = update.effective_user

    # Thank user
    await update.message.reply_text(
        "✅ *Готово! Спасибо за честные ответы.*\n\n"
        "Профиль уже отправлен — скоро увидишь свой персональный курс 🔥",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    # Send profile to admin
    if ADMIN_ID:
        profile_text = build_profile(answers)
        user_info = f"От: @{user.username or '—'} | {user.full_name} | id: {user.id}"

        # Send human-readable profile
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 *НОВЫЙ ПРОФИЛЬ*\n_{user_info}_\n\n{profile_text}",
            parse_mode="Markdown"
        )

        # Send JSON for the app
        json_str = build_json(answers)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"```json\n{json_str}\n```",
            parse_mode="Markdown"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Окей, анкета отменена. Напиши /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    states = {i: [MessageHandler(filters.TEXT & ~filters.COMMAND, HANDLERS[i])] for i in range(20)}

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states=states,
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start))

    logger.info("Bot started")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
