from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def meters_keyboard(meters: list) -> InlineKeyboardMarkup:
    buttons = []
    for meter in meters:
        buttons.append([
            InlineKeyboardButton(
                text=f"{meter['service_name']} ({meter['serial_number']})",
                callback_data=f"meter:{meter['id']}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="Отмена", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_reading_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data="confirm_reading"),
            InlineKeyboardButton(text="Отмена", callback_data="cancel"),
        ]
    ])
