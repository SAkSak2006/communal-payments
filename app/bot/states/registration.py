from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_account = State()
    waiting_for_phone = State()
    waiting_for_confirm = State()
