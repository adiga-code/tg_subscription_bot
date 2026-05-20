from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_email = State()


class ResidentQuestionnaire(StatesGroup):
    waiting_name = State()
    waiting_profession = State()
    waiting_experience = State()
    waiting_value = State()
    waiting_contacts = State()
    waiting_instagram = State()


class PaymentFlow(StatesGroup):
    waiting_email = State()


class AdminBroadcast(StatesGroup):
    waiting_text = State()
    confirm = State()


class AdminGrant(StatesGroup):
    waiting_user_id = State()
    waiting_plan = State()


class AdminDelete(StatesGroup):
    waiting_user_id = State()
