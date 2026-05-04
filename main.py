import asyncio
import random
import hashlib
import re
import os
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

# ==================== КОНФИГ ====================
TOKEN = os.getenv("TOKEN", "8527906938:AAG97Gj3RuMhjOMWLHZ7nFX4GqjK06pOlFI")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==================== ДАННЫЕ ====================
user_last_command = {}
user_coin_history = {}
user_num_history = {}
user_ship_timestamps = {}

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
    if user_id not in user_num_history:
        user_num_history[user_id] = []
    user_num_history[user_id].append(num)
    if len(user_num_history[user_id]) > 10:
        user_num_history[user_id] = user_num_history[user_id][-10:]

def check_num_spam(user_id):
    history = user_num_history.get(user_id, [])
    if len(history) >= 3:
        now = datetime.now().timestamp()
        last_time = user_last_command.get(f"{user_id}_num", 0)
        if now - last_time < 10:
            user_last_command[f"{user_id}_num"] = now
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

def generate_fish_text(length=20):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
    return ''.join(random.choice(chars) for _ in range(length))

# ==================== КЛАВИАТУРА МЕНЮ ====================

def get_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🪙 Монетка", callback_data="flip"),
        InlineKeyboardButton(text="🔢 Число", callback_data="num"),
    )
    builder.row(
        InlineKeyboardButton(text="💘 Шипперим", callback_data="ship"),
        InlineKeyboardButton(text="🎲 Куб", callback_data="dice"),
    )
    builder.row(
        InlineKeyboardButton(text="🎰 Слоты", callback_data="slot"),
    )
    return builder.as_markup()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🎲 RND Bot запущен!\n/menu — список режимов")

@dp.message(Command("menu"))
@dp.message(F.text == "меню")
async def cmd_menu(message: Message):
    await message.answer("🎲 RND BOT", reply_markup=get_menu_keyboard())

@dp.callback_query(F.data == "flip")
async def cb_flip(callback: types.CallbackQuery):
    await callback.answer()
    await flip_command(callback.message)

@dp.callback_query(F.data == "num")
async def cb_num(callback: types.CallbackQuery):
    await callback.answer()
    await num_command(callback.message, "1-100")

@dp.callback_query(F.data == "ship")
async def cb_ship(callback: types.CallbackQuery):
    await callback.answer()
    await ship_command(callback.message, "")

@dp.callback_query(F.data == "dice")
async def cb_dice(callback: types.CallbackQuery):
    await callback.answer()
    await dice_command(callback.message)

@dp.callback_query(F.data == "slot")
async def cb_slot(callback: types.CallbackQuery):
    await callback.answer()
    await slot_command(callback.message)

@dp.message(Command("flip"))
@dp.message(F.text.in_(["монетка", "монета"]))
async def cmd_flip(message: Message):
    await flip_command(message)

@dp.message(Command("num"))
@dp.message(F.text == "рандом число")
async def cmd_num(message: Message):
    await num_command(message, "1-100")

@dp.message(Command("ship"))
@dp.message(F.text.in_(["шипперим", "шип"]))
async def cmd_ship(message: Message):
    await ship_command(message, "")

@dp.message(Command("dice"))
@dp.message(F.text.in_(["куб", "кубик"]))
async def cmd_dice(message: Message):
    await dice_command(message)

@dp.message(Command("slot"))
@dp.message(F.text.in_(["слоты", "крутить"]))
async def cmd_slot(message: Message):
    await slot_command(message)

# ==================== РЕЖИМЫ ====================

async def flip_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_cooldown(user_id):
        msg = await message.answer("Подожди 3 секунды.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    rare = get_rare_easter_egg()
    date_egg = get_date_easter_egg()

    if rare == "shy":
        msg = await message.answer("...")
        await asyncio.sleep(5)
    else:
        msg = await message.answer("🎰 МОНЕТКА")

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

    update_coin_history(user_id, result)
    series_count, series_text = get_coin_series(user_id)

    response = result

    if series_text:
        response += f"\n{series_text}"

    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    if date_egg == "new_year":
        response += "\nС новым годом. Новый бросок."
    elif date_egg == "april_fool":
        response += "\nПервое апреля. Никому не верь."
    elif date_egg == "halloween":
        response += "\nТыква смотрит."

    if rare == "caps":
        response = response.upper()

    await msg.edit_text(response)


async def num_command(message: Message, args_text=""):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_cooldown(user_id):
        msg = await message.answer("Подожди 3 секунды.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    rare = get_rare_easter_egg()
    date_egg = get_date_easter_egg()

    # Парсим диапазон из аргументов
    match = re.match(r"(-?\d+)[-\s](-?\d+)", args_text)
    if match:
        min_val = int(match.group(1))
        max_val = int(match.group(2))
    else:
        min_val, max_val = 1, 100

    if min_val > max_val:
        min_val, max_val = max_val, min_val

    if rare == "shy":
        msg = await message.answer("...")
        await asyncio.sleep(5)
    else:
        msg = await message.answer("🎲 РАНДОМ ЧИСЛО")

    if date_egg == "nye":
        next_year = get_moscow_time().year + 1
        num = next_year
    else:
        num = random.randint(min_val, max_val)

    if rare == "double":
        num2 = random.randint(min_val, max_val)
        response = f"Число: {num} и {num2}. Выбирай."
        if not (min_val == 1 and max_val == 100):
            response += f"\nДиапазон: {min_val} – {max_val}"
    else:
        if min_val == 1 and max_val == 100:
            response = str(num)
        else:
            response = f"Число: {num}\nДиапазон: {min_val} – {max_val}"

        if num == min_val:
            response += "\nМинимум."
        elif num == max_val:
            response += "\nМаксимум."
        elif (max_val - min_val) % 2 == 0 and num == (min_val + max_val) // 2:
            response += "\nРовно середина."

    digit_egg = get_digit_easter_egg(num)
    if digit_egg:
        response += f"\n{digit_egg}"

    update_num_history(user_id, num)
    spam_text = check_num_spam(user_id)
    if spam_text:
        response += f"\n{spam_text}"

    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    if date_egg == "nye":
        response += "\nСкоро."
    elif date_egg == "halloween":
        response += "\nТыква смотрит."

    if rare == "caps":
        response = response.upper()

    await msg.edit_text(response)


async def ship_command(message: Message, args_text=""):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if chat_id == user_id:
        await message.answer("Этот режим работает только в группе.")
        return

    if is_cooldown(user_id):
        msg = await message.answer("Подожди 3 секунды.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    spam_text = update_ship_timestamps(user_id)

    msg = await message.answer("💘 ШИППЕРИМ")

    # Парсим имена
    parts = args_text.split()
    if parts:
        name1 = parts[0].lstrip("@")
        name2 = parts[1] if len(parts) > 1 else f"user_{random.randint(1000, 9999)}"
    else:
        name1 = f"user_{random.randint(1000, 9999)}"
        name2 = f"user_{random.randint(1000, 9999)}"

    target1 = parts[0] if parts else ""
    target2 = parts[1] if len(parts) > 1 else ""

    if target1 and target2 and target1.lower() == target2.lower():
        percent = 100
    elif target2.lower() in ["пицца", "pizza"]:
        percent = 94
    elif target2.lower() in ["понедельник", "monday"]:
        percent = 3
    elif target2.lower() in ["сон", "sleep"]:
        percent = 99
    elif target2.lower() in ["работа", "work"]:
        percent = 12
    elif target2.lower() in ["зарплата", "salary"]:
        percent = 88
    elif target2.lower() in ["дедлайн", "deadline"]:
        percent = 1
    elif target2.lower() in ["выходные", "weekend"]:
        percent = 97
    elif target2.lower() in ["wi-fi", "wifi"]:
        percent = 100
    elif target2.lower() in ["бот", "bot"]:
        percent = 50
    else:
        percent = hash_names(name1, name2)

    verdict = get_ship_verdict(percent)
    response = f"@{name1} + @{name2}\n{percent}%\n{verdict}"

    # Пасхалки для шиппера
    if target2.lower() in ["пицца", "pizza"]:
        response += "\nПицца любит всех."
    elif target2.lower() in ["понедельник", "monday"]:
        response += "\nПонедельник не любит никого."
    elif target1 and target2 and target1.lower() == target2.lower():
        response += "\nСам с собой. Идеально."
    elif target2.lower() in ["сон", "sleep"]:
        response += "\nСон — это святое."
    elif target2.lower() in ["работа", "work"]:
        response += "\nРабота не любит никого."
    elif target2.lower() in ["зарплата", "salary"]:
        response += "\nЖди."
    elif target2.lower() in ["дедлайн", "deadline"]:
        response += "\nБеги."
    elif target2.lower() in ["выходные", "weekend"]:
        response += "\nПочти дома."
    elif target2.lower() in ["wi-fi", "wifi"]:
        response += "\nБез связи никак."
    elif target2.lower() in ["бот", "bot"]:
        response += "\nОн всего лишь код."

    digit_egg = get_digit_easter_egg(percent)
    if digit_egg:
        response += f"\n{digit_egg}"

    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    date_egg = get_date_easter_egg()
    if date_egg == "valentine":
        response += "\nСегодня всё возможно."
    elif date_egg == "halloween":
        response += "\nТыква смотрит."

    if spam_text:
        response += f"\n{spam_text}"

    await msg.edit_text(response)


async def dice_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_cooldown(user_id):
        msg = await message.answer("Подожди 3 секунды.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    dice_faces = [
        "┌───────┐\n│ ●     │\n│       │\n│     ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│       │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│   ●   │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│ ●   ● │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ●   ● │\n│ ● ● ● │\n│ ●   ● │\n└───────┘",
        "┌───────┐\n│ ● ● ● │\n│ ●   ● │\n│ ● ● ● │\n└───────┘",
    ]

    result = random.randint(1, 6)
    msg = await message.answer("🎲 КУБ\n\nКручу...")

    for face in dice_faces:
        await asyncio.sleep(0.25)
        await msg.edit_text(f"🎲 КУБ\n\n{face}\n\nКручу...")

    response = f"🎲 КУБ — РЕЗУЛЬТАТ\n\n{dice_faces[result-1]}\n\nВыпало: {result}"

    if result == 6:
        response += "\nМаксимум."
    elif result == 1:
        response += "\nМинимум."

    digit_egg = get_digit_easter_egg(result)
    if digit_egg:
        response += f"\n{digit_egg}"

    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    await msg.edit_text(response)


async def slot_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_cooldown(user_id):
        msg = await message.answer("Подожди 3 секунды.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    symbols = ["7️⃣", "🍒", "🍍", "🍏", "🍆", "💣"]
    s1 = random.choice(symbols)
    s2 = random.choice(symbols)
    s3 = random.choice(symbols)

    msg = await message.answer("🎰 СЛОТЫ\n\n[🎰] [❓] [❓]\n\nКручу...")

    for i in range(3):
        await asyncio.sleep(0.35)
        spin_state = ["[❓]", "[❓]", "[❓]"]
        spin_state[i] = "[🎰]"
        if i >= 1:
            spin_state[0] = f"[{s1}]"
        if i >= 2:
            spin_state[1] = f"[{s2}]"
        text = f"🎰 СЛОТЫ\n\n{spin_state[0]} {spin_state[1]} {spin_state[2]}\n\nКручу..."
        await msg.edit_text(text)

    await asyncio.sleep(0.35)
    await msg.edit_text(f"🎰 СЛОТЫ\n\n[{s1}] [{s2}] [🎰]\n\nЗамедляются...")

    await asyncio.sleep(0.35)
    await msg.edit_text(f"🎰 СЛОТЫ\n\n[{s1}] [{s2}] [{s3}]\n\nПочти...")

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

    time_egg = get_time_easter_egg()
    if time_egg:
        response += f"\n{time_egg}"

    await msg.edit_text(response)


async def special_67(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or ""

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

    msg = await message.answer(frames[0])

    for i, frame in enumerate(frames[1:], 1):
        await asyncio.sleep(1.5)
        text = frame
        if i == len(frames) - 1 and username and chat_id != user_id:
            text = f"@{username}: {frame}"
        await msg.edit_text(text)


async def fish_command(message: Message):
    fish_text = generate_fish_text(random.randint(15, 40))
    await message.answer(fish_text)


# ==================== ОБРАБОТЧИК ВСЕХ ТЕКСТОВЫХ СООБЩЕНИЙ ====================

@dp.message(F.text)
async def handle_text(message: Message):
    text = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id

    # "67" — спецрежим
    if text == "67":
        await special_67(message)
        return

    # "рыба"
    if text.lower() == "рыба":
        await fish_command(message)
        return

    # Монетка с параметрами
    if text.startswith("монетка "):
        extra = text[8:]
        if extra == "честно":
            await message.answer("Ребро.\nЧестно.")
            return
        elif extra == "судьба":
            await message.answer("Орёл.\nСудьба не спрашивает.")
            return
        elif extra == "жизнь":
            await message.answer("Орёл.\nЖиви.")
            return
        elif extra == "любовь":
            await message.answer("Решка.\nЛюби.")
            return
        elif extra.startswith("или "):
            options = extra[4:].split()
            choice = options[0] if options else "первое"
            await message.answer(f"Орёл.\n{choice}.")
            return

    # Число с диапазоном
    match = re.match(r"(?:/num|рандом число)\s+(.+)", text)
    if match:
        await num_command(message, match.group(1))
        return

    # Шипперим с параметрами
    match = re.match(r"(?:/ship|шипперим|шип)\s+(.+)", text)
    if match:
        await ship_command(message, match.group(1))
        return


# ==================== ЗАПУСК ====================

async def main():
    print("RND Bot запущен на aiogram!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
