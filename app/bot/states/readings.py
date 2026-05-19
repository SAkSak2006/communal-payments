from aiogram.fsm.state import State, StatesGroup


class ReadingStates(StatesGroup):
    waiting_for_meter = State()
    waiting_for_value = State()
    waiting_for_confirm = State()
