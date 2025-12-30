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