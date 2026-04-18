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
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "0"))

# ── BLOCK INTROS ──────────────────────────────────────────────────────────────
BLOCK_INTROS = {
    # After q2 (before block 2 starts at q3)
    3: "Отлично! ⚡\n\nПервая часть позади. Теперь немного про то, как ты думаешь — как принимаешь решения, как разбираешься в новом, что делаешь когда что-то непонятно. Тут тоже нет правильных ответов — просто интересно как устроена твоя голова 😄",
    # After q5 (before block 3 starts at q6)
    6: "Супер, идём дальше! 🔥\n\nСейчас хочу узнать что тебя по-настоящему зажигает — что вдохновляет, что мотивирует, а что наоборот выбивает из колеи. Это поможет мне сделать подарок таким, чтобы тебе было реально интересно, а не скучно.",
    # After q8 (before block 4 starts at q9)
    9: "Ты отлично справляешься! 🙌\n\nСледующий блок — про твой подход к делам и задачам. Любишь порядок или комфортно в творческом хаосе? Нравится когда всё чётко или когда можно делать как хочешь? Сейчас узнаем 😊",
    # After q10 (before block 5 starts at q11)
    11: "Почти готово! 💫\n\nОсталось совсем немного. Сейчас пару вопросов про то, как ты общаешься с людьми — в компании, в классе, с подругами. Как себя ведёшь, что чувствуешь, как реагируешь. Просто интересно какая ты в жизни 🙂",
    # After q12 (before block 6 starts at q13)
    13: "Последний блок! 🎉\n\nСовсем чуть-чуть осталось. Несколько вопросов про будущее — как ты его представляешь, что чувствуешь когда думаешь о нём. Без давления, просто честно как есть.",
}

# ── STATES ────────────────────────────────────────────────────────────────────
class Survey(StatesGroup):
    q1  = State(); q2  = State(); q3  = State(); q4  = State(); q5  = State()
    q6  = State(); q7  = State(); q8  = State(); q9  = State(); q10 = State()
    q11 = State(); q12 = State(); q13 = State(); q14 = State()

STATES = [
    Survey.q1,  Survey.q2,  Survey.q3,  Survey.q4,  Survey.q5,
    Survey.q6,  Survey.q7,  Survey.q8,  Survey.q9,  Survey.q10,
    Survey.q11, Survey.q12, Survey.q13, Survey.q14,
]

TOTAL = 14

# ── QUESTIONS ─────────────────────────────────────────────────────────────────
QUESTIONS = [
    # BLOCK 1 — Энергия (q1-q2)
    {
        "key": "free_day",
        "text": "Представь: завтра неожиданно нет школы. Весь день твой. Что сделаешь первым делом?",
        "keys": [
            ["Позову подруг — куда-нибудь пойдём или потусуемся"],
            ["Останусь дома, займусь чем-нибудь своим"],
            ["Буду действовать по настроению — заранее не знаю"],
            ["Наконец займусь тем, до чего руки не доходят"],
        ],
    },
    {
        "key": "new_people",
        "text": "Тебя позвали на день рождения, где почти никого не знаешь. Ты...",
        "keys": [
            ["Ок, прикольно — познакомлюсь с новыми людьми"],
            ["Немного нервно, но пойду и справлюсь"],
            ["Буду держаться рядом с тем, кого знаю"],
            ["Честно — скорее всего найду повод не идти 😅"],
        ],
    },

    # BLOCK 2 — Как думаешь (q3-q5)
    {
        "key": "task_no_reason",
        "text": "Тебе задали задание, но не объяснили зачем оно нужно. Что делаешь?",
        "keys": [
            ["Делаю как сказали — разберусь по ходу"],
            ["Сначала спрошу зачем, без смысла не могу"],
            ["Придумаю себе причину сама и буду делать под неё"],
            ["Скорее всего отложу до последнего момента"],
        ],
    },
    {
        "key": "learning_style",
        "text": "Ты узнаёшь что-то новое — как тебе удобнее?",
        "keys": [
            ["Сразу пробую делать — на ошибках понятнее"],
            ["Сначала изучаю всё что есть, потом только делаю"],
            ["Прошу кого-то показать на примере"],
            ["Смотрю видосы или reels пока не дойдёт 😄"],
        ],
    },
    {
        "key": "decisions",
        "text": "Как обычно принимаешь решения?",
        "keys": [
            ["Чувствую нутром — если что-то не так, значит не так"],
            ["Думаю логически, взвешиваю что выгоднее"],
            ["Спрашиваю подругу или маму что думают"],
            ["Долго сомневаюсь и в итоге кто-то решает за меня"],
        ],
    },

    # BLOCK 3 — Что заводит (q6-q8)
    {
        "key": "what_matters",
        "text": "Что для тебя важнее в любом деле?",
        "keys": [
            ["Чтобы получилось красиво и круто — качество важно"],
            ["Чтобы мне было интересно в процессе"],
            ["Чтобы это кто-то увидел и оценил"],
            ["Чтобы побыстрее и без лишних заморочек"],
        ],
    },
    {
        "key": "quit_reason",
        "text": "Из-за чего ты обычно бросаешь дело на полпути?",
        "keys": [
            ["Стало скучно или слишком просто"],
            ["Стало слишком сложно и непонятно"],
            ["Перестало казаться важным — зачем вообще"],
            ["Появилось что-то более интересное"],
        ],
    },
    {
        "key": "praise_reaction",
        "text": "Тебя похвалили за работу. Что внутри?",
        "keys": [
            ["Приятно, но главное что сама довольна результатом"],
            ["Это важно — похвала реально заряжает двигаться дальше"],
            ["Немного неловко — не люблю быть в центре внимания"],
            ["Сразу думаю что можно было сделать лучше"],
        ],
    },

    # BLOCK 4 — Порядок vs хаос (q9-q10)
    {
        "key": "room_style",
        "text": "Как выглядит твой стол или комната чаще всего?",
        "keys": [
            ["Всё на своих местах — иначе не могу нормально думать"],
            ["Творческий беспорядок, но я знаю где что лежит"],
            ["Периодически убираю, потом снова накапливается"],
            ["Обычно хаос, но мне норм 😂"],
        ],
    },
    {
        "key": "no_rules",
        "text": "Тебе говорят: делай проект как хочешь, никаких правил. Это...",
        "keys": [
            ["Мечта — обожаю когда никто не ограничивает"],
            ["Немного пугает — хочется хоть каких-то рамок"],
            ["Зависит от темы"],
            ["Скорее напрягает — не знаю с чего начать"],
        ],
    },

    # BLOCK 5 — Общение (q11-q12)
    {
        "key": "group_role",
        "text": "В компании или в классе ты чаще...",
        "keys": [
            ["Предлагаю что делать и как-то сама оказываюсь главной"],
            ["Поддерживаю чужие идеи и помогаю их сделать"],
            ["Наблюдаю и говорю когда спросят"],
            ["По-разному — зависит от людей и ситуации"],
        ],
    },
    {
        "key": "disagree",
        "text": "Подруга говорит что-то, с чем ты не согласна. Ты...",
        "keys": [
            ["Сразу говорю что думаю — честность важнее"],
            ["Промолчу — зачем портить настроение"],
            ["Скажу аккуратно, подбирая слова"],
            ["Зависит от того, насколько это важно для меня"],
        ],
    },

    # BLOCK 6 — Будущее (q13-q14)
    {
        "key": "future_feeling",
        "text": "Когда думаешь о будущем — что чувствуешь чаще всего?",
        "keys": [
            ["Интерес — столько всего интересного впереди"],
            ["Немного тревожно — много непонятного"],
            ["Ничего особенного — живу сегодняшним днём"],
            ["Вдохновение — у меня уже есть какой-то план"],
        ],
    },
    {
        "key": "self_now",
        "text": "Что из этого больше всего про тебя?",
        "keys": [
            ["Я знаю чего хочу — просто ещё не всё получилось"],
            ["Я пока ищу себя — непонятно кто я и чего хочу"],
            ["Мне важнее кайфовать от процесса, а не от цели"],
            ["Хочу сразу всего и не могу выбрать одно"],
        ],
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

def build_profile(answers: dict, user_info: dict) -> str:
    name = user_info.get("first_name", "—")
    username = user_info.get("username", "—")
    uid = user_info.get("id", "—")
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🧠 Профиль: {name} (@{username})",
        f"Telegram ID: {uid}",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
        "── ЭНЕРГИЯ ──",
        f"🌤 Свободный день: {answers.get('free_day','—')}",
        f"👥 Новые люди: {answers.get('new_people','—')}\n",
        "── КАК ДУМАЕТ ──",
        f"❓ Задание без причины: {answers.get('task_no_reason','—')}",
        f"📚 Стиль обучения: {answers.get('learning_style','—')}",
        f"🤔 Решения: {answers.get('decisions','—')}\n",
        "── ЧТО ЗАВОДИТ ──",
        f"⭐ Важно в деле: {answers.get('what_matters','—')}",
        f"🚪 Бросает из-за: {answers.get('quit_reason','—')}",
        f"🏅 Реакция на похвалу: {answers.get('praise_reaction','—')}\n",
        "── ПОРЯДОК vs ХАОС ──",
        f"🗂 Комната: {answers.get('room_style','—')}",
        f"🎨 Без правил: {answers.get('no_rules','—')}\n",
        "── ОБЩЕНИЕ ──",
        f"👑 Роль в группе: {answers.get('group_role','—')}",
        f"💬 Не согласна: {answers.get('disagree','—')}\n",
        "── БУДУЩЕЕ ──",
        f"🔭 Чувство о будущем: {answers.get('future_feeling','—')}",
        f"🪞 Про себя сейчас: {answers.get('self_now','—')}\n",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)

def build_json(answers: dict, user_info: dict) -> str:
    # Психографические выводы
    energy = answers.get("free_day", "")
    social = answers.get("new_people", "")
    thinking = answers.get("decisions", "")
    structure = answers.get("room_style", "")
    motivation = answers.get("what_matters", "")
    group = answers.get("group_role", "")

    # Простая интерпретация
    introvert = any(w in social for w in ["держаться", "повод не идти"])
    structured = any(w in structure for w in ["на своих местах", "нормально думать"])
    internal_motivation = any(w in motivation for w in ["интересно в процессе", "сама довольна"])
    leader = "главной" in group

    profile = {
        "name": user_info.get("first_name", ""),
        "telegram_id": user_info.get("id", ""),
        "psycho_profile": {
            "energy_type": "интроверт" if introvert else "экстраверт",
            "structure_need": "высокая" if structured else "низкая",
            "motivation_type": "внутренняя" if internal_motivation else "внешняя",
            "group_role": "лидер" if leader else "поддержка/наблюдатель",
            "decision_style": thinking,
            "learning_style": answers.get("learning_style", ""),
        },
        "quit_trigger": answers.get("quit_reason", ""),
        "praise_reaction": answers.get("praise_reaction", ""),
        "future_orientation": answers.get("future_feeling", ""),
        "self_identity": answers.get("self_now", ""),
        "raw_answers": answers,
    }
    return json.dumps(profile, ensure_ascii=False, indent=2)

# ── HANDLERS ──────────────────────────────────────────────────────────────────
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
        "Во-первых, мне правда интересно чем ты живёшь и что тебя увлекает. "
        "А во-вторых — я готовлю тебе подарок, и чтобы он получился максимально "
        "классным и подходящим именно тебе, мне нужно кое-что про тебя знать.\n\n"
        "Займёт минут 10, не больше. Отвечай честно — "
        "здесь нет правильных и неправильных ответов. "
        "Все ответы останутся только у меня, обещаю 🤝\n\n"
        "Готова? Поехали! 🚀"
    )
    await message.answer(intro, reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5)

    q = QUESTIONS[0]
    await message.answer(
        f"*Вопрос 1/{TOTAL}*\n\n{q['text']}\n\n`{progress(1)}`",
        parse_mode="Markdown",
        reply_markup=make_kb(q["keys"])
    )
    await state.set_state(Survey.q1)

async def handle_q(message: Message, state: FSMContext, step: int):
    data = await state.get_data()
    answers = data.get("answers", {})
    answers[KEYS[step - 1]] = message.text.strip()
    await state.update_data(answers=answers)

    next_step = step + 1

    if next_step <= TOTAL:
        # Send block intro if needed
        if next_step in BLOCK_INTROS:
            await message.answer(
                BLOCK_INTROS[next_step],
                reply_markup=ReplyKeyboardRemove()
            )
            await asyncio.sleep(0.8)

        q = QUESTIONS[next_step - 1]
        await message.answer(
            f"*Вопрос {next_step}/{TOTAL}*\n\n{q['text']}\n\n`{progress(next_step)}`",
            parse_mode="Markdown",
            reply_markup=make_kb(q["keys"])
        )
        await state.set_state(STATES[next_step - 1])
    else:
        user_info = data.get("user_info", {})
        await finish(message, answers, user_info)
        await state.clear()

async def finish(message: Message, answers: dict, user_info: dict):
    first_name = user_info.get("first_name", "")

    await message.answer(
        f"Машенька, спасибо тебе огромное! 🤍\n\n"
        "Ты ответила на все вопросы — это реально помогло мне узнать тебя намного лучше. "
        "Теперь я смогу сделать подарок таким, чтобы он подошёл именно тебе — "
        "с учётом всего, что ты рассказала.\n\n"
        "Я очень рад что у нас получился такой разговор, пусть даже и в переписке. "
        "Люблю тебя, обнимаю крепко. Скоро увидишь что получится! 🎁",
        reply_markup=ReplyKeyboardRemove()
    )

    if ADMIN_ID:
        bot = message.bot
        profile_text = build_profile(answers, user_info)
        json_str = build_json(answers, user_info)

        await bot.send_message(
            ADMIN_ID,
            f"📥 Маша заполнила анкету!\n\n{profile_text}",
        )
        await bot.send_message(
            ADMIN_ID,
            f"```json\n{json_str}\n```",
            parse_mode="Markdown"
        )

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
