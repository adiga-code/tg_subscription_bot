from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_email = State()


class AdminBroadcast(StatesGroup):
    waiting_text = State()
    confirm = State()


class AdminGrant(StatesGroup):
    waiting_user_id = State()
    waiting_plan = State()
