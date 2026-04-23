import logging
import re
import json
import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BotCommand
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN      = os.environ.get("BOT_TOKEN", "")
ADMIN_ID       = int(os.environ.get("ADMIN_ID", "0"))
GONKA_API_KEY  = os.environ.get("GONKA_API_KEY", "")
GONKA_BASE_URL = "https://proxy.gonkabroker.com/v1"
GONKA_MODEL    = "Qwen/Qwen3-235B-A22B-Instruct-2507-FP8"

# ── PROGRESS BAR ─────────────────────────────────────────────────────────────
def progress(step, total=14):
    filled = round(step / total * 8)
    empty  = 8 - filled
    return "🟣" * filled + "⚪" * empty + f"  {step}/{total}"

# ── BLOCK INTROS ─────────────────────────────────────────────────────────────
BLOCK_INTROS = {
    2:  "Отлично! ⚡\n\nПервая часть позади. Теперь немного про то, как ты думаешь — как принимаешь решения, как разбираешься в новом, что делаешь когда что-то непонятно. Правильных ответов нет — просто интересно как устроена твоя голова 😄",
    5:  "Супер, идём дальше! 🔥\n\nСейчас хочу узнать что тебя по-настоящему зажигает — что вдохновляет, что мотивирует, а что наоборот выбивает из колеи.",
    8:  "Ты отлично справляешься! 🙌\n\nСледующий блок — про твой подход к делам. Любишь порядок или комфортно в хаосе? Нравится когда всё чётко или когда можно делать как хочешь?",
    10: "Почти готово! 💫\n\nОсталось совсем немного. Пара вопросов про то, как ты общаешься с людьми — в компании, в классе, с подругами.",
    12: "Последний блок! 🎉\n\nДва вопроса про будущее — как ты его представляешь и что чувствуешь когда думаешь о нём.",
}

# ── STATES ───────────────────────────────────────────────────────────────────
class Survey(StatesGroup):
    confirm  = State()
    reminder = State()
    q1  = State(); q2  = State(); q3  = State(); q4  = State(); q5  = State()
    q6  = State(); q7  = State(); q8  = State(); q9  = State(); q10 = State()
    q11 = State(); q12 = State(); q13 = State(); q14 = State()

Q_STATES = [
    Survey.q1,  Survey.q2,  Survey.q3,  Survey.q4,  Survey.q5,
    Survey.q6,  Survey.q7,  Survey.q8,  Survey.q9,  Survey.q10,
    Survey.q11, Survey.q12, Survey.q13, Survey.q14,
]
TOTAL = 14

# ── QUESTIONS ────────────────────────────────────────────────────────────────
QUESTIONS = [
    # Block 1 — Энергия
    {"key": "free_day",
     "text": "🌤 Представь: завтра неожиданно нет школы. Весь день твой.\nЧто сделаешь первым делом?",
     "keys": [["👯 Позову подруг — куда-нибудь пойдём или потусуемся"],
              ["🏠 Останусь дома, займусь чем-нибудь своим"],
              ["🎲 Буду действовать по настроению — заранее не знаю"],
              ["✨ Наконец займусь тем, до чего руки не доходят"]]},

    {"key": "new_people",
     "text": "🎂 Тебя позвали на день рождения, где почти никого не знаешь. Ты...",
     "keys": [["😊 Ок, прикольно — познакомлюсь с новыми людьми"],
              ["😬 Немного нервно, но пойду и справлюсь"],
              ["🤝 Буду держаться рядом с тем, кого знаю"],
              ["😅 Честно — скорее всего найду повод не идти"]]},

    # Block 2 — Как думаешь
    {"key": "task_no_reason",
     "text": "📋 Тебе задали задание, но не объяснили зачем оно нужно.\nЧто делаешь?",
     "keys": [["➡️ Делаю как сказали — разберусь по ходу"],
              ["🤔 Сначала спрошу зачем, без смысла не могу"],
              ["💡 Придумаю себе причину сама и буду делать под неё"],
              ["⏳ Скорее всего отложу до последнего момента"]]},

    {"key": "learning_style",
     "text": "📖 Ты узнаёшь что-то новое — как тебе удобнее?",
     "keys": [["🛠 Сразу пробую делать — на ошибках понятнее"],
              ["📚 Сначала изучаю всё что есть, потом только делаю"],
              ["👀 Прошу кого-то показать на примере"],
              ["📱 Смотрю видосы или reels пока не дойдёт 😄"]]},

    {"key": "decisions",
     "text": "⚖️ Как обычно принимаешь решения?",
     "keys": [["💫 Чувствую нутром — если что-то не так, значит не так"],
              ["🧮 Думаю логически, взвешиваю что выгоднее"],
              ["💬 Спрашиваю подругу или маму что думают"],
              ["😵 Долго сомневаюсь и в итоге кто-то решает за меня"]]},

    # Block 3 — Что заводит
    {"key": "what_matters",
     "text": "⭐ Что для тебя важнее в любом деле?",
     "keys": [["✨ Чтобы получилось красиво и круто — качество важно"],
              ["🎯 Чтобы мне было интересно в процессе"],
              ["👏 Чтобы это кто-то увидел и оценил"],
              ["⚡ Чтобы побыстрее и без лишних заморочек"]]},

    {"key": "quit_reason",
     "text": "🚪 Из-за чего ты обычно бросаешь дело на полпути?",
     "keys": [["😴 Стало скучно или слишком просто"],
              ["😤 Стало слишком сложно и непонятно"],
              ["🤷 Перестало казаться важным — зачем вообще"],
              ["🦋 Появилось что-то более интересное"]]},

    {"key": "praise_reaction",
     "text": "🏅 Тебя похвалили за работу. Что внутри?",
     "keys": [["😌 Приятно, но главное что сама довольна результатом"],
              ["🚀 Это важно — похвала реально заряжает двигаться дальше"],
              ["🙈 Немного неловко — не люблю быть в центре внимания"],
              ["🔍 Сразу думаю что можно было сделать лучше"]]},

    # Block 4 — Порядок vs хаос
    {"key": "room_style",
     "text": "🗂 Как выглядит твой стол или комната чаще всего?",
     "keys": [["✅ Всё на своих местах — иначе не могу нормально думать"],
              ["🎨 Творческий беспорядок, но я знаю где что лежит"],
              ["🔄 Периодически убираю, потом снова накапливается"],
              ["😂 Обычно хаос, но мне норм"]]},

    {"key": "no_rules",
     "text": "🎨 Тебе говорят: делай проект как хочешь, никаких правил. Это...",
     "keys": [["🥳 Мечта — обожаю когда никто не ограничивает"],
              ["😰 Немного пугает — хочется хоть каких-то рамок"],
              ["🤔 Зависит от темы"],
              ["😅 Скорее напрягает — не знаю с чего начать"]]},

    # Block 5 — Общение
    {"key": "group_role",
     "text": "👥 В компании или в классе ты чаще...",
     "keys": [["👑 Предлагаю что делать и как-то сама оказываюсь главной"],
              ["🤝 Поддерживаю чужие идеи и помогаю их сделать"],
              ["👁 Наблюдаю и говорю когда спросят"],
              ["🎭 По-разному — зависит от людей и ситуации"]]},

    {"key": "disagree",
     "text": "💬 Подруга говорит что-то, с чем ты не согласна. Ты...",
     "keys": [["🗣 Сразу говорю что думаю — честность важнее"],
              ["🤐 Промолчу — зачем портить настроение"],
              ["🌸 Скажу аккуратно, подбирая слова"],
              ["⚖️ Зависит от того, насколько это важно для меня"]]},

    # Block 6 — Будущее
    {"key": "future_feeling",
     "text": "🔭 Когда думаешь о будущем — что чувствуешь чаще всего?",
     "keys": [["🌟 Интерес — столько всего интересного впереди"],
              ["😟 Немного тревожно — много непонятного"],
              ["☀️ Ничего особенного — живу сегодняшним днём"],
              ["🗺 Вдохновение — у меня уже есть какой-то план"]]},

    {"key": "self_now",
     "text": "🪞 Что из этого больше всего про тебя?",
     "keys": [["🎯 Я знаю чего хочу — просто ещё не всё получилось"],
              ["🔍 Я пока ищу себя — непонятно кто я и чего хочу"],
              ["🌊 Мне важнее кайфовать от процесса, а не от цели"],
              ["🌈 Хочу сразу всего и не могу выбрать одно"]]},
]

KEYS = [q["key"] for q in QUESTIONS]

# ── HELPERS ──────────────────────────────────────────────────────────────────
def make_kb(rows):
    if not rows:
        return ReplyKeyboardRemove()
    buttons = [[KeyboardButton(text=t) for t in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

async def send_question(message: Message, idx: int):
    if idx in BLOCK_INTROS:
        await message.answer(BLOCK_INTROS[idx], reply_markup=ReplyKeyboardRemove())
        await asyncio.sleep(0.7)
    q = QUESTIONS[idx]
    await message.answer(
        f"{q['text']}\n\n{progress(idx + 1)}",
        reply_markup=make_kb(q["keys"])
    )

# ── CLAUDE ANALYSIS ───────────────────────────────────────────────────────────
async def get_ai_analysis(answers: dict, user_info: dict) -> str:
    if not GONKA_API_KEY:
        return "⚠️ GONKA_API_KEY не задан — аналитика недоступна."

    name = user_info.get("first_name", "пользователь")
    answers_text = "\n".join([f"• {k}: {v}" for k, v in answers.items()])

    prompt = f"""Ты опытный детский психолог и специалист по профориентации.

Перед тобой ответы {name} (12 лет) на психографическую анкету.

ОТВЕТЫ:
{answers_text}

Напиши подробный психологический портрет на русском языке. Структура:

1. **Тип личности и темперамент** — кратко опиши кто она: интроверт/экстраверт, как управляет энергией
2. **Стиль мышления** — как думает, принимает решения, обрабатывает информацию
3. **Мотивация** — что её заряжает, что выбивает из колеи, внутренняя или внешняя мотивация
4. **Отношение к структуре** — нужны ли правила и порядок или предпочитает свободу
5. **Социальный профиль** — роль в группе, как строит отношения, как реагирует на конфликт
6. **Ориентация на будущее** — как относится к планированию и неопределённости
7. **Рекомендации** — как лучше всего с ней работать, какой формат обучения зайдёт, чего избегать
8. **Одна ключевая сильная сторона** — то, на что стоит опираться

Пиши живо, конкретно, без воды. Избегай общих фраз. Объём — примерно 400-500 слов."""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GONKA_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GONKA_API_KEY}",
                    "content-type": "application/json",
                },
                json={
                    "model": GONKA_MODEL,
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                # Strip Qwen3 thinking tags if present
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
                return text
    except Exception as e:
        logger.error(f"AI API error: {e}")
        return f"⚠️ Ошибка при получении аналитики: {e}"

# ── HANDLERS ─────────────────────────────────────────────────────────────────
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    first_name = message.from_user.first_name or "Машенька"
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
        "Это дядя Петя. Я сделал для тебя небольшую анкету — специально, "
        "чтобы узнать тебя получше. Мы всё-таки семья, а общаемся так редко 🙂\n\n"
        "Мне правда интересно чем ты живёшь и что тебя увлекает. "
        "А ещё — я готовлю тебе подарок, и чтобы он получился максимально "
        "классным и подходящим именно тебе, мне нужно кое-что про тебя знать.\n\n"
        "Займёт минут 10, не больше. Отвечай честно — "
        "здесь нет правильных и неправильных ответов. "
        "Все ответы останутся только у меня, обещаю 🤝\n\n"
        "Есть сейчас 10 свободных минут?"
    )
    await message.answer(intro, reply_markup=make_kb([
        ["✅ Да, готова! Поехали!"],
        ["🕐 Давай чуть попозже"]
    ]))
    await state.set_state(Survey.confirm)

async def handle_confirm(message: Message, state: FSMContext):
    text = message.text.lower()

    if "позже" in text or "потом" in text:
        await message.answer(
            "Хорошо, не спеши! 🙂\n\nКогда напомнить?",
            reply_markup=make_kb([
                ["🌙 Сегодня вечером"],
                ["🌅 Завтра утром"],
                ["✍️ Я сама напишу когда буду готова"]
            ])
        )
        await state.set_state(Survey.reminder)
        return

    await message.answer("Отлично, начинаем! 🎉", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.3)
    await send_question(message, 0)
    await state.set_state(Survey.q1)

async def handle_reminder(message: Message, state: FSMContext):
    text = message.text.lower()
    now = datetime.now()

    if "вечером" in text:
        remind_at = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if remind_at <= now:
            remind_at += timedelta(days=1)
        delay = (remind_at - now).total_seconds()
        label = "сегодня в 20:00"
    elif "утром" in text or "завтра" in text:
        remind_at = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        delay = (remind_at - now).total_seconds()
        label = "завтра в 10:00"
    else:
        await message.answer(
            "Хорошо! Буду ждать 🙂\nКогда будешь готова — просто напиши /start",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return

    await message.answer(
        f"Окей, напомню {label} 🔔\nДо встречи!",
        reply_markup=ReplyKeyboardRemove()
    )

    chat_id = message.chat.id
    bot = message.bot
    await state.clear()

    # Schedule reminder
    async def send_reminder():
        await asyncio.sleep(delay)
        await bot.send_message(
            chat_id,
            "Привет! 👋 Это снова дядя Петя.\n\nНу что, сейчас готова пройти анкету? Займёт всего 10 минут 🙂",
            reply_markup=make_kb([["✅ Да, готова! Поехали!"], ["🕐 Давай чуть попозже"]])
        )

    asyncio.create_task(send_reminder())

async def handle_q(message: Message, state: FSMContext, idx: int):
    data = await state.get_data()
    answers = data.get("answers", {})
    answers[KEYS[idx]] = message.text.strip()
    await state.update_data(answers=answers)

    next_idx = idx + 1
    if next_idx < TOTAL:
        await send_question(message, next_idx)
        await state.set_state(Q_STATES[next_idx])
    else:
        user_info = data.get("user_info", {})
        await finish(message, answers, user_info, message.bot)
        await state.clear()

async def finish(message: Message, answers: dict, user_info: dict, bot: Bot):
    # Thank Masha — warm goodbye, no mention of data
    await message.answer(
        "Машенька, спасибо тебе огромное! 🤍\n\n"
        "Ты ответила на все вопросы — это правда помогло мне.\n"
        "Люблю тебя, обнимаю крепко. Скоро узнаешь что это было 🎁",
        reply_markup=ReplyKeyboardRemove()
    )

    if not ADMIN_ID:
        return

    name = user_info.get("first_name", "—")
    username = user_info.get("username", "—")

    # 1. Raw answers
    answers_text = "\n".join([f"• {k}: {v}" for k, v in answers.items()])
    await bot.send_message(
        ADMIN_ID,
        f"📥 *{name} (@{username}) заполнила анкету!*\n\n{answers_text}",
        parse_mode="Markdown"
    )

    # 2. JSON
    profile = {
        "name": name,
        "telegram_id": user_info.get("id"),
        "answers": answers,
    }
    await bot.send_message(
        ADMIN_ID,
        f"```json\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n```",
        parse_mode="Markdown"
    )

    # 3. Claude psychological analysis
    await bot.send_message(ADMIN_ID, "🧠 Генерирую психологический анализ...")
    analysis = await get_ai_analysis(answers, user_info)
    # Split if too long for Telegram
    if len(analysis) > 4000:
        for i in range(0, len(analysis), 4000):
            await bot.send_message(ADMIN_ID, analysis[i:i+4000])
    else:
        await bot.send_message(ADMIN_ID, f"🧠 *Психологический портрет {name}*\n\n{analysis}", parse_mode="Markdown")

# ── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    await bot.set_my_commands([
        BotCommand(command="start",   description="Начать анкету"),
        BotCommand(command="restart", description="Начать заново"),
    ])

    dp.message.register(cmd_start,       Command(commands=["start", "restart"]))
    dp.message.register(handle_confirm,  Survey.confirm,  F.text)
    dp.message.register(handle_reminder, Survey.reminder, F.text)

    for i, st in enumerate(Q_STATES):
        def make_handler(idx):
            async def handler(message: Message, state: FSMContext):
                await handle_q(message, state, idx)
            return handler
        dp.message.register(make_handler(i), st, F.text)

    logger.info(f"Bot started. ADMIN_ID={ADMIN_ID}")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
