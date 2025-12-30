import asyncio
import logging
import os
from typing import Dict, Set

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("8480146150:AAGN8rtXcs7wGOrozUjZrZuVHkp9Mdecun0")
ADMIN_ID = int(os.getenv("7925556738", "0"))
CHANNEL_1 = os.getenv("@shaxa_muzik1")  # masalan: @kanal_1
CHANNEL_2 = os.getenv("@uzbek_hakerr")  # masalan: @kanal_2

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# RAMdagi "bazalar"
VIDEO_BY_CODE: Dict[str, str] = {}       # code -> file_id
VIEWS_BY_CODE: Dict[str, int] = {}       # code -> count
USERS_BY_CODE: Dict[str, Set[int]] = {}  # code -> {user_ids}

# Admin bilan video yuklash jarayoni uchun holatlar
ADMIN_STATE: Dict[int, Dict] = {}  # admin_id -> {"step": "...", "temp_file_id": "..."}


async def check_subscription(user_id: int) -> bool:
    """
    Foydalanuvchi ikkala kanalda ham obunami yoki yo'q – shuni tekshiradi.
    """
    try:
        member1 = await bot.get_chat_member(CHANNEL_1, user_id)
        member2 = await bot.get_chat_member(CHANNEL_2, user_id)
        ok1 = member1.status in ("member", "administrator", "creator")
        ok2 = member2.status in ("member", "administrator", "creator")
        return ok1 and ok2
    except Exception as e:
        logging.warning(f"check_subscription error: {e}")
        return False


def sub_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="Kanal 1", url=f"https://t.me/{CHANNEL_1.lstrip('@')}"),
        InlineKeyboardButton(text="Kanal 2", url=f"https://t.me/{CHANNEL_2.lstrip('@')}"),
    )
    kb.row(
        InlineKeyboardButton(text="Obunani tekshirish", callback_data="check_sub")
    )
    return kb.as_markup()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Salom!

"
        "Botdan to'liq foydalanish uchun quyidagi 2 ta kanalga obuna bo'ling, "
        "so'ng "Obunani tekshirish" tugmasini bosing."
    )
    await message.answer(text, reply_markup=sub_keyboard())


@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(call: CallbackQuery):
    user_id = call.from_user.id
    is_subscribed = await check_subscription(user_id)
    if is_subscribed:
        await call.message.edit_text(
            "Rahmat! Endi kod yuboring (masalan: 48)."
        )
    else:
        await call.answer("Hali hamma kanallarga obuna bo‘lmadingiz!", show_alert=True)


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="Video qo'shish", callback_data="admin_add_video"),
    )
    kb.row(
        InlineKeyboardButton(text="Statistika", callback_data="admin_stats"),
    )
    await message.answer("Admin menyu:", reply_markup=kb.as_markup())


@dp.callback_query(F.data == "admin_add_video")
async def admin_add_video(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    ADMIN_STATE[ADMIN_ID] = {"step": "wait_video"}
    await call.message.answer(
        "Video yuboring.

"
        "1) Avval video yuborasiz.
"
        "2) Keyin bot sizdan kod so'raydi."
    )
    await call.answer()


@dp.message(F.video)
async def admin_got_video(message: Message):
    if message.from_user.id != ADMIN_ID:
        # oddiy foydalanuvchi video yuborsa – e'tibor bermaymiz yoki xabar beramiz
        return

    state = ADMIN_STATE.get(ADMIN_ID)
    if not state or state.get("step") != "wait_video":
        await message.answer("Avval /admin -> "Video qo'shish" menyusidan kiring.")
        return
file_id = message.video.file_id
    ADMIN_STATE[ADMIN_ID]["temp_file_id"] = file_id
    ADMIN_STATE[ADMIN_ID]["step"] = "wait_code"
    await message.answer("Video olindi. Endi shu video uchun kod yuboring (masalan: 48).")


@dp.message(F.text & F.text.regexp(r"^d+$"))
async def handle_code(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Admin kod kiritayotgan bo'lishi mumkin (video biriktirish uchun)
    state = ADMIN_STATE.get(ADMIN_ID)
    if user_id == ADMIN_ID and state and state.get("step") == "wait_code":
        file_id = state.get("temp_file_id")
        if not file_id:
            await message.answer("Xato: video topilmadi. Qaytadan urinib ko'ring.")
            ADMIN_STATE.pop(ADMIN_ID, None)
            return

        code = text
        VIDEO_BY_CODE[code] = file_id
        VIEWS_BY_CODE.setdefault(code, 0)
        USERS_BY_CODE.setdefault(code, set())

        ADMIN_STATE.pop(ADMIN_ID, None)
        await message.answer(f"Video muvaffaqiyatli saqlandi. Kod: {code}")
        return

    # Oddiy foydalanuvchi – avval obunani tekshir
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        await message.answer(
            "Avval kanallarga obuna bo'ling, so'ng "Obunani tekshirish" tugmasini bosing.",
            reply_markup=sub_keyboard(),
        )
        return

    code = text
    file_id = VIDEO_BY_CODE.get(code)
    if not file_id:
        await message.answer("Bu kod bo‘yicha video topilmadi. Admin bilan bog‘laning.")
        return

    # statistika
    VIEWS_BY_CODE[code] = VIEWS_BY_CODE.get(code, 0) + 1
    USERS_BY_CODE.setdefault(code, set()).add(user_id)

    await message.answer_video(file_id)


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    if not VIDEO_BY_CODE:
        await call.message.answer("Hozircha hech qanday video saqlanmagan.")
        await call.answer()
        return

    lines = ["Statistika:"]
    for code, file_id in VIDEO_BY_CODE.items():
        views = VIEWS_BY_CODE.get(code, 0)
        users = len(USERS_BY_CODE.get(code, set()))
        lines.append(f"• Kod {code}: {views} marta ko‘rilgan, {users} ta foydalanuvchi.")
    await call.message.answer("
".join(lines))
    await call.answer()


async def main():
    await dp.start_polling(bot)


if name == "main":
    asyncio.run(main())