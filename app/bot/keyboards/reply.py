from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Подать показания"), KeyboardButton(text="💰 Баланс")],
        [KeyboardButton(text="📋 История оплат"), KeyboardButton(text="📈 Тарифы")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
    ],
    resize_keyboard=True,
)

confirm_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да, всё верно"), KeyboardButton(text="Нет, отмена")],
    ],
    resize_keyboard=True,
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отмена")],
    ],
    resize_keyboard=True,
)

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
        [KeyboardButton(text="Отмена")],
    ],
    resize_keyboard=True,
)

remove_keyboard = ReplyKeyboardRemove()
