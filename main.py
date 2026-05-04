import asyncio
import random
import hashlib
import re
from datetime import datetime, timezone, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

# ==================== КОНФИГ ====================
TOKEN = "8527906938:AAG97Gj3RuMhjOMWLHZ7nFX4GqjK06pOlFI"
bot = Bot(token=TOKEN)

# ==================== ДАННЫЕ ====================
user_last_command = {}        # user_id -> timestamp последней команды
user_coin_history = {}        # user_id -> list последних бросков монетки
user_num_history = {}         # user_id -> list последних чисел
user_ship_timestamps = {}     # user_id -> list timestamps шипов

COOLDOWN_SEC = 3
MOSCOW_TZ = timezone(timedelta(hours=3))

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_moscow_time():
    return datetime.now(MOSCOW_TZ)

def is_cooldown(user_id):
    now = datetime.now().timestamp()
    if user_id in user_last_command:
        if now - user_last_command[user_id] < COOLDOWN_SEC:
            return True
    user_last_command[user_id] = now
    return False

def hash_names(name1, name2):
    """Детерминированный хеш для шиппера."""
    names = sorted([name1.lower(), name2.lower()])
    combined = f"{names[0]}_{names[1]}"
    hash_val = int(hashlib.md5(combined.encode()).hexdigest(), 16)
    return hash_val % 101

def get_ship_verdict(percent):
    if percent == 0:
        return "Нулевая совместимость."
    elif percent <= 10:
        return "Почти ничего."
    elif percent <= 25:
        return "Так себе."
    elif percent <= 40:
        return "Ниже среднего."
    elif percent <= 60:
        return "Средне."
    elif percent <= 75:
        return "Выше среднего."
    elif percent <= 90:
        return "Огонь."
    elif percent <= 99:
        return "Почти идеал."
    else:
        return "Идеальная совместимость."

def get_digit_easter_egg(num):
    """Цифровые пасхалки."""
    eggs = {
        52: "Пятьдесят два.",
        67: "Six seven. 🤲",
        69: "♋️",
        404: "Не найдено. ⚠️",
        88: "Восемьдесят восемь. Бесконечность на боку.",
        14: "Четырнадцать. Половина от двадцати восьми.",
        28: "Двадцать восемь. Половина от пятидесяти шести.",
        56: "Пятьдесят шесть. Две двадцать восемь.",
    }
    return eggs.get(num, "")

def get_time_easter_egg():
    """Временные пасхалки."""
    now = get_moscow_time()
    hour = now.hour
    minute = now.minute

    if hour == 4 and minute == 20:
        return "4:20. Иди спать."
    elif 0 <= hour < 6:
        return "Иди спать."
    elif hour == 9 and minute == 0:
        return "Девять утра."
    elif hour == 12 and minute == 0:
        return "Полдень."
    return ""

def get_date_easter_egg():
    """Датовые пасхалки."""
    now = get_moscow_time()
    month = now.month
    day = now.day

    if month == 1 and day == 1:
        return "new_year"
    elif month == 2 and day == 14:
        return "valentine"
    elif month == 4 and day == 1:
        return "april_fool"
    elif month == 10 and day == 31:
        return "halloween"
    elif month == 12 and day == 31:
        return "nye"
    return ""

def get_rare_easter_egg():
    """Случайная редкая пасхалка (1% шанс)."""
    roll = random.randint(1, 100)
    if roll == 1:
        return "glitch"
    elif roll == 2:
        return "caps"
    elif roll == 3:
        return "shy"
    elif roll == 4:
        return "double"
    return ""

def update_coin_history(user_id, result):
    if user_id not in user_coin_history:
        user_coin_history[user_id] = []
    user_coin_history[user_id].append(result)
    if len(user_coin_history[user_id]) > 10:
        user_coin_history[user_id] = user_coin_history[user_id][-10:]

def get_coin_series(user_id):
    history = user_coin_history.get(user_id, [])
    if not history:
        return 0, ""
    last = history[-1]
    count = 0
    for r in reversed(history):
        if r == last:
            count += 1
        else:
            break
    if count == 3:
        return count, f"{last}. Третий раз."
    elif count == 5:
        return count, f"{last}. Пятый раз. 1 к 32."
    return count, ""

def update_num_history(user_id, num):
    if user_id not in num_history:
        num_history[user_id] = []
    num_history[user_id].append(num)
    if len(num_history[user_id]) > 10:
        num_history[user_id] = num_history[user_id][-10:]

def check_num_spam(user_id):
    history = num_history.get(user_id, [])
    if len(history) >= 3:
        recent = history[-3:]
        now = datetime.now().timestamp()
        if now - user_last_command.get(f"{user_id}_num", 0) < 10:
            return "Ты ищешь что-то конкретное?"
    user_last_command[f"{user_id}_num"] = datetime.now().timestamp()
    return ""

def update_ship_timestamps(user_id):
    if user_id not in user_ship_timestamps:
        user_ship_timestamps[user_id] = []
    now = datetime.now().timestamp()
    user_ship_timestamps[user_id].append(now)
    user_ship_timestamps[user_id] = [t for t in user_ship_timestamps[user_id] if now - t < 60]
    if len(user_ship_timestamps[user_id]) >= 5:
        return "Пятый шип за минуту. Отдохни."
    return ""

# ==================== РЕЖИМЫ ====================

async def flip_command(chat_id, user_id, extra_text=""):
    if is_cooldown(user_id):
        msg = await bot.send_message(chat_id, "Подожди 3 секунды.")
        await asyncio.sleep(5)
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramError:
            pass
        return

    # Редкая пасхалка
    rare = get_rare_easter_egg()

    if rare == "shy":
        msg = await bot.send_message(chat_id, "...")
        await asyncio.sleep(5)
        # Продолжаем после паузы
    else:
        msg = await bot.send_message(chat_id, "🎰 МОНЕТКА")

    # Определяем результат
    date_egg = get_date_easter_egg()
    if date_egg == "april_fool":
        result = "Ребро"
    elif date_egg == "new_year":
        result = "Орёл"
    else:
        roll = random.randint(1, 1000)
        if roll <= 495:
            result = "Орёл"
        elif roll <= 990:
            result = "Решка"
        else:
            result = "Ребро"

    # Серии
    update_coin_history(user_id, result)
    series_count, series_text = get_coin_series(user_id)

    # Сборка ответа
    response = result

    # Серийная пасхалка
    if series_text:
        response += f"\n{series_text}"

    # Временная пасхалка
    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    # Датовая пасхалка
    if date_egg == "new_year":
        response += "\nС новым годом. Новый бросок."
    elif date_egg == "april_fool":
        response += "\nПервое апреля. Никому не верь."
    elif date_egg == "halloween":
        response += "\nТыква смотрит."

    # Голос судьбы (капс)
    if rare == "caps":
        response = response.upper()

    # Редактируем сообщение
    await bot.edit_message_text(response, chat_id, msg.message_id)


async def num_command(chat_id, user_id, min_val, max_val):
    if is_cooldown(user_id):
        msg = await bot.send_message(chat_id, "Подожди 3 секунды.")
        await asyncio.sleep(5)
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramError:
            pass
        return

    rare = get_rare_easter_egg()
    date_egg = get_date_easter_egg()

    if rare == "shy":
        msg = await bot.send_message(chat_id, "...")
        await asyncio.sleep(5)
    else:
        msg = await bot.send_message(chat_id, "🎲 РАНДОМ ЧИСЛО")

    # Проверка диапазона
    if min_val > max_val:
        min_val, max_val = max_val, min_val

    # Дата: 31 декабря
    if date_egg == "nye":
        next_year = get_moscow_time().year + 1
        num = next_year
    else:
        num = random.randint(min_val, max_val)

    # Редкая пасхалка: двойной бросок
    if rare == "double":
        num2 = random.randint(min_val, max_val)
        response = f"Число: {num} и {num2}. Выбирай."
        if min_val != 1 or max_val != 100:
            response += f"\nДиапазон: {min_val} – {max_val}"
    else:
        if min_val == 1 and max_val == 100:
            response = str(num)
        else:
            response = f"Число: {num}\nДиапазон: {min_val} – {max_val}"

        # Середина, минимум, максимум
        if num == min_val:
            response += "\nМинимум."
        elif num == max_val:
            response += "\nМаксимум."
        elif (max_val - min_val) % 2 == 0 and num == (min_val + max_val) // 2:
            response += "\nРовно середина."

    # Цифровая пасхалка
    digit_egg = get_digit_easter_egg(num)
    if digit_egg:
        response += f"\n{digit_egg}"

    # Серийная проверка
    update_num_history(user_id, num)
    spam_text = check_num_spam(user_id)
    if spam_text:
        response += f"\n{spam_text}"

    # Временная пасхалка
    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    # Датовая пасхалка
    if date_egg == "nye":
        response += "\nСкоро."
    elif date_egg == "halloween":
        response += "\nТыква смотрит."

    if rare == "caps":
        response = response.upper()

    await bot.edit_message_text(response, chat_id, msg.message_id)


async def ship_command(chat_id, user_id, target1=None, target2=None):
    if chat_id == user_id:
        await bot.send_message(chat_id, "Этот режим работает только в группе.")
        return

    if is_cooldown(user_id):
        msg = await bot.send_message(chat_id, "Подожди 3 секунды.")
        await asyncio.sleep(5)
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramError:
            pass
        return

    spam_text = update_ship_timestamps(user_id)

    msg = await bot.send_message(chat_id, "💘 ШИППЕРИМ")

    # Определяем цель
    if target1 and target1.startswith("@"):
        name1 = target1[1:]
    else:
        # Случайный участник
        name1 = f"user_{random.randint(1000, 9999)}"

    if target2 and target2.startswith("@"):
        name2 = target2[1:]
    elif target2:
        name2 = target2
    else:
        name2 = f"user_{random.randint(1000, 9999)}"

    # Процент
    if target1 and target2 and target1 == target2:
        percent = 100
    elif target2 and target2.lower() in ["пицца", "pizza"]:
        percent = 94
    elif target2 and target2.lower() in ["понедельник", "monday"]:
        percent = 3
    elif target2 and target2.lower() in ["сон", "sleep"]:
        percent = 99
    elif target2 and target2.lower() in ["работа", "work"]:
        percent = 12
    elif target2 and target2.lower() in ["зарплата", "salary"]:
        percent = 88
    elif target2 and target2.lower() in ["дедлайн", "deadline"]:
        percent = 1
    elif target2 and target2.lower() in ["выходные", "weekend"]:
        percent = 97
    elif target2 and target2.lower() in ["wi-fi", "wifi"]:
        percent = 100
    elif target2 and target2.lower() in ["бот", "bot"]:
        percent = 50
    else:
        percent = hash_names(name1, name2)

    verdict = get_ship_verdict(percent)

    response = f"@{name1} + @{name2}\n{percent}%\n{verdict}"

    # Нецифровые пасхалки для шиппера
    if target2 and target2.lower() in ["пицца", "pizza"]:
        response += "\nПицца любит всех."
    elif target2 and target2.lower() in ["понедельник", "monday"]:
        response += "\nПонедельник не любит никого."
    elif target1 and target2 and target1 == target2:
        response += "\nСам с собой. Идеально."
    elif target2 and target2.lower() in ["сон", "sleep"]:
        response += "\nСон — это святое."
    elif target2 and target2.lower() in ["работа", "work"]:
        response += "\nРабота не любит никого."
    elif target2 and target2.lower() in ["зарплата", "salary"]:
        response += "\nЖди."
    elif target2 and target2.lower() in ["дедлайн", "deadline"]:
        response += "\nБеги."
    elif target2 and target2.lower() in ["выходные", "weekend"]:
        response += "\nПочти дома."
    elif target2 and target2.lower() in ["wi-fi", "wifi"]:
        response += "\nБез связи никак."
    elif target2 and target2.lower() in ["бот", "bot"]:
        response += "\nОн всего лишь код."

    # Цифровая пасхалка
    digit_egg = get_digit_easter_egg(percent)
    if digit_egg:
        response += f"\n{digit_egg}"

    # Временная пасхалка
    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    # Датовая пасхалка
    date_egg = get_date_easter_egg()
    if date_egg == "valentine":
        response += "\nСегодня всё возможно."
    elif date_egg == "halloween":
        response += "\nТыква смотрит."

    # Спам шиппера
    if spam_text:
        response += f"\n{spam_text}"

    await bot.edit_message_text(response, chat_id, msg.message_id)


async def dice_command(chat_id, user_id):
    if is_cooldown(user_id):
        msg = await bot.send_message(chat_id, "Подожди 3 секунды.")
        await asyncio.sleep(5)
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramError:
            pass
        return

    # Анимация куба: 7 кадров
    dice_faces = [
        "┌───────┐\n│ ●     │\n│       │\n│     ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│       │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│   ●   │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│ ●   ● │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│ ● ● ● │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ● ● ● │\n│ ●   ● │\n│ ● ● ● │\n└───────┘",
    ]

    result = random.randint(1, 6)
    msg = await bot.send_message(chat_id, "🎲 КУБ\n\nКручу...")

    for i, face in enumerate(dice_faces):
        await asyncio.sleep(0.25)
        try:
            await bot.edit_message_text(f"🎲 КУБ\n\n{face}\n\nКручу...", chat_id, msg.message_id)
        except TelegramError:
            pass

    # Финальный кадр
    response = f"🎲 КУБ — РЕЗУЛЬТАТ\n\n{dice_faces[result-1]}\n\nВыпало: {result}"

    if result == 6:
        response += "\nМаксимум."
    elif result == 1:
        response += "\nМинимум."

    # Цифровая пасхалка
    digit_egg = get_digit_easter_egg(result)
    if digit_egg:
        response += f"\n{digit_egg}"

    # Временная пасхалка
    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    await bot.edit_message_text(response, chat_id, msg.message_id)


async def slot_command(chat_id, user_id):
    if is_cooldown(user_id):
        msg = await bot.send_message(chat_id, "Подожди 3 секунды.")
        await asyncio.sleep(5)
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except TelegramError:
            pass
        return

    symbols = ["7️⃣", "🍒", "🍍", "🍏", "🍆", "💣"]

    # Спиним три барабана
    s1 = random.choice(symbols)
    s2 = random.choice(symbols)
    s3 = random.choice(symbols)

    msg = await bot.send_message(chat_id, "🎰 СЛОТЫ\n\n[🎰] [❓] [❓]\n\nКручу...")

    # Анимация
    for i in range(3):
        await asyncio.sleep(0.35)
        spin_state = ["[❓]", "[❓]", "[❓]"]
        spin_state[i] = "[🎰]"
        if i >= 1:
            spin_state[0] = f"[{s1}]"
        if i >= 2:
            spin_state[1] = f"[{s2}]"
        text = f"🎰 СЛОТЫ\n\n{spin_state[0]} {spin_state[1]} {spin_state[2]}\n\nКручу..."
        try:
            await bot.edit_message_text(text, chat_id, msg.message_id)
        except TelegramError:
            pass

    # Замедление
    await asyncio.sleep(0.35)
    try:
        await bot.edit_message_text(f"🎰 СЛОТЫ\n\n[{s1}] [{s2}] [🎰]\n\nЗамедляются...", chat_id, msg.message_id)
    except TelegramError:
        pass

    await asyncio.sleep(0.35)
    try:
        await bot.edit_message_text(f"🎰 СЛОТЫ\n\n[{s1}] [{s2}] [{s3}]\n\nПочти...", chat_id, msg.message_id)
    except TelegramError:
        pass

    # Результат
    await asyncio.sleep(0.35)

    if "💣" in [s1, s2, s3]:
        response = f"🎰 СЛОТЫ — РЕЗУЛЬТАТ\n\n[{s1}] [{s2}] [{s3}]\n\n💥 ПРОИГРЫШ\nБомба всё испортила."
    elif s1 == s2 == s3:
        if s1 == "7️⃣":
            response = f"🎰 СЛОТЫ — РЕЗУЛЬТАТ\n\n[{s1}] [{s2}] [{s3}]\n\n🌟 ДЖЕКПОТ! ТРИ СЕМЁРКИ!"
        else:
            response = f"🎰 СЛОТЫ — РЕЗУЛЬТАТ\n\n[{s1}] [{s2}] [{s3}]\n\n🔥 ТРИ ОДИНАКОВЫХ! Круто!"
    elif s1 == s2 or s2 == s3 or s1 == s3:
        response = f"🎰 СЛОТЫ — РЕЗУЛЬТАТ\n\n[{s1}] [{s2}] [{s3}]\n\n🙂 Два совпадения."
    else:
        response = f"🎰 СЛОТЫ — РЕЗУЛЬТАТ\n\n[{s1}] [{s2}] [{s3}]\n\n😐 Ни одного совпадения."

    # Временная пасхалка
    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    await bot.edit_message_text(response, chat_id, msg.message_id)


async def special_67(chat_id, user_id, username=""):
    """Спецрежим 67 — анимация 15 секунд."""
    frames = [
        "Шесть...",
        "Шесть... ☝️",
        "Шесть... ✊",
        "Семь...",
        "Семь... ☝️",
        "Семь... ✊",
        "🤲 Six seven.",
        "🤲 Шесть-семь.",
        "🤲 67.",
        "🤲 Шесть-семь. 67.",
    ]

    msg = await bot.send_message(chat_id, frames[0])

    for i, frame in enumerate(frames[1:], 1):
        await asyncio.sleep(1.5)
        try:
            text = frame
            if i == len(frames) - 1 and username and chat_id != user_id:
                text = f"@{username}: {frame}"
            await bot.edit_message_text(text, chat_id, msg.message_id)
        except TelegramError:
            pass


def generate_fish_text(length=20):
    """Генерирует случайную строку из букв, цифр и символов."""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
    return ''.join(random.choice(chars) for _ in range(length))


async def fish_command(chat_id):
    """Пасхалка 'рыба' — генерация случайной строки."""
    fish_text = generate_fish_text(random.randint(15, 40))
    await bot.send_message(chat_id, fish_text)


# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

async def handle_message(update):
    """Обработчик входящих сообщений."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    username = update.message.from_user.username or ""

    # Проверка: просто "67"
    if text == "67":
        await special_67(chat_id, user_id, username)
        return

    # Проверка: "рыба"
    if text.lower() == "рыба":
        await fish_command(chat_id)
        return

    # Меню
    if text in ["/menu", "меню"]:
        keyboard = [
            [InlineKeyboardButton("🪙 Монетка", callback_data="flip"),
             InlineKeyboardButton("🔢 Число", callback_data="num")],
            [InlineKeyboardButton("💘 Шипперим", callback_data="ship"),
             InlineKeyboardButton("🎲 Куб", callback_data="dice")],
            [InlineKeyboardButton("🎰 Слоты", callback_data="slot")],
        ]
        await bot.send_message(chat_id, "🎲 RND BOT", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Монетка: /flip, монетка, монета
    if text in ["/flip", "монетка", "монета"]:
        await flip_command(chat_id, user_id)
        return

    # Монетка с параметрами
    if text.startswith("монетка ") or text.startswith("/flip "):
        extra = text.split(" ", 1)[1] if " " in text else ""

        # Пасхалки
        if extra == "честно":
            msg = await bot.send_message(chat_id, "Ребро.\nЧестно.")
            return
        elif extra == "судьба":
            msg = await bot.send_message(chat_id, "Орёл.\nСудьба не спрашивает.")
            return
        elif extra == "жизнь":
            msg = await bot.send_message(chat_id, "Орёл.\nЖиви.")
            return
        elif extra == "любовь":
            msg = await bot.send_message(chat_id, "Решка.\nЛюби.")
            return
        elif extra.startswith("или "):
            options = extra[4:].split()
            choice = options[0] if options else "первое"
            msg = await bot.send_message(chat_id, f"Орёл.\n{choice}.")
            return

        # По умолчанию — простой бросок
        await flip_command(chat_id, user_id)
        return

    # Число
    if text == "/num" or text == "рандом число":
        await num_command(chat_id, user_id, 1, 100)
        return

    # Число с диапазоном: /num 5-56, рандом число 5-56, рандом число 10 200
    num_pattern = r"(?:/num|рандом число)\s+(-?\d+)[-\s](-?\d+)"
    num_match = re.match(num_pattern, text)
    if num_match:
        min_val = int(num_match.group(1))
        max_val = int(num_match.group(2))
        await num_command(chat_id, user_id, min_val, max_val)
        return

    # Числовые пасхалки
    if text.startswith("рандом число "):
        extra = text[len("рандом число "):]
        if "сколько мне лет" in extra:
            msg = await bot.send_message(chat_id, "Число: 27. Столько.")
            return
        elif "когда женюсь" in extra:
            msg = await bot.send_message(chat_id, "Число: 2031. Жди.")
            return
        elif "сколько заработаю" in extra:
            msg = await bot.send_message(chat_id, "Число: 300. Тысяч.")
            return
        elif "в чём смысл" in extra or "в чем смысл" in extra:
            msg = await bot.send_message(chat_id, "Число: 42. Ответ на главный вопрос.")
            return
        elif extra in ["1-1", "1 1"]:
            msg = await bot.send_message(chat_id, "Число: 1. Выбора не было.")
            return
        elif extra in ["1-2", "1 2"]:
            msg = await bot.send_message(chat_id, "Число: 2. Мог бы монетку кинуть.")
            return

    # Шипперим: /ship, шипперим, шип
    if text in ["/ship", "шипперим", "шип"]:
        await ship_command(chat_id, user_id)
        return

    # Шипперим с тегами
    ship_pattern = r"(?:/ship|шипперим|шип)\s+(@?\S+)(?:\s+(@?\S+))?"
    ship_match = re.match(ship_pattern, text)
    if ship_match:
        target1 = ship_match.group(1)
        target2 = ship_match.group(2) if ship_match.group(2) else None
        await ship_command(chat_id, user_id, target1, target2)
        return

    # Куб: /dice, куб, кубик
    if text in ["/dice", "куб", "кубик"]:
        await dice_command(chat_id, user_id)
        return

    # Слоты: /slot, слоты, крутить
    if text in ["/slot", "слоты", "крутить"]:
        await slot_command(chat_id, user_id)
        return


# ==================== ЗАПУСК ====================

async def main():
    """Основной цикл бота."""
    print("RND Bot запущен!")
    offset = 0
    while True:
        try:
            updates = await bot.get_updates(offset=offset, timeout=30)
            for update in updates:
                await handle_message(update)
                offset = update.update_id + 1
        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
