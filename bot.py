import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from googletrans import Translator
from gtts import gTTS

API_TOKEN = "SENING_TOKENING"
ADMIN_ID = 7925556738

CHANNELS = ["@shaxa_muzik1", "@uzbek_hakerr"]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

translator = Translator()
users = set()
user_texts = {}

# --- Obuna tekshirish ---
async def check_subscriptions(user_id: int) -> bool:
    for channel in CHANNELS:
        member = await bot.get_chat_member(channel, user_id)
        if member.status not in ("member", "administrator", "creator"):
            return False
    return True

# --- /start ---
@dp.message(Command("start"))
async def start_cmd(message: Message):
    users.add(message.from_user.id)

    if not await check_subscriptions(message.from_user.id):
        kb = InlineKeyboardMarkup(row_width=1)
        for ch in CHANNELS:
            kb.add(InlineKeyboardButton("📢 Kanalga o‘tish", url=f"https://t.me/{ch[1:]}"))
        kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
        await message.answer("❗ Iltimos, 2 ta kanalga obuna bo‘ling:", reply_markup=kb)
        return

    await message.answer("✍️ Matn yuboring")

# --- Tekshirish tugmasi ---
@dp.callback_query(F.data == "check_sub")
async def recheck_sub(call: CallbackQuery):
    if await check_subscriptions(call.from_user.id):
        await call.message.answer("✅ Obuna tasdiqlandi!\n✍️ Endi matn yuboring")
    else:
        await call.answer("❌ Hali obuna emassiz", show_alert=True)

# --- Matn qabul qilish ---
@dp.message(F.text)
async def get_text(message: Message):
    if message.text.startswith("/"):
        return

    if not await check_subscriptions(message.from_user.id):
        await start_cmd(message)
        return

    user_texts[message.from_user.id] = message.text

    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("🇬🇧 English", callback_data="en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="ru"),
        InlineKeyboardButton("🇺🇿 Uzbek", callback_data="uz")
    )
    await message.answer("🌍 Qaysi tilga tarjima qilay?", reply_markup=kb)

# --- Tarjima + ovoz ---
@dp.callback_query(F.data.in_(["en", "ru", "uz"]))
async def translate_voice(call: CallbackQuery):
    text = user_texts.get(call.from_user.id)
    if not text:
        await call.answer("❌ Matn topilmadi", show_alert=True)
        return

    translated = translator.translate(text, dest=call.data).text
    tts = gTTS(translated, lang=call.data)
    file_name = f"{call.from_user.id}.ogg"
    tts.save(file_name)

    with open(file_name, "rb") as voice:
        await bot.send_voice(call.from_user.id, voice)

    os.remove(file_name)

# --- Admin statistika ---
@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"📊 Foydalanuvchilar soni: {len(users)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))