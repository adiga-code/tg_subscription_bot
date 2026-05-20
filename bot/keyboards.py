from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

from bot.config import PLANS


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📋 Тарифы")],
            [KeyboardButton(text="💬 Поддержка")],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📋 Тарифы")],
            [KeyboardButton(text="💬 Поддержка")],
            [KeyboardButton(text="🔧 Админ-панель")],
        ],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def role_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Я резидент", callback_data="role:resident")],
        [InlineKeyboardButton(text="2️⃣ Я участник", callback_data="role:participant")],
    ])


def pay_participant_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить подписку — 2 499 ₽/мес.", callback_data="pay:1m")],
    ])


def plans_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, plan in PLANS.items():
        save_text = f"  ({plan['save']})" if plan["save"] else ""
        label = f"{plan['name']} — {plan['price']:,} ₽{save_text}".replace(",", " ")
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"plan:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pay_button(plan_key: str) -> InlineKeyboardMarkup:
    plan = PLANS[plan_key]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Оплатить {plan['price']:,} ₽".replace(",", " "),
            callback_data=f"pay:{plan_key}",
        )],
    ])


def payment_link_keyboard(url: str, plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_payment:{plan_key}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")],
    ])


def support_keyboard(support_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать менеджеру", url=f"https://t.me/{support_username}")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="faq")],
    ])


def faq_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back:support")],
    ])


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Подписчики", callback_data="admin:users")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton(text="✅ Выдать подписку", callback_data="admin:grant")],
        [InlineKeyboardButton(text="❌ Отозвать подписку", callback_data="admin:revoke")],
        [InlineKeyboardButton(text="🗑️ Удалить пользователя", callback_data="admin:delete")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
    ])


def admin_plan_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, plan in PLANS.items():
        buttons.append([InlineKeyboardButton(text=plan["name"], callback_data=f"admin_plan:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def resident_application_keyboard(tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"res_grant:{tg_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"res_reject:{tg_id}"),
        ]
    ])


def confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast:cancel"),
        ]
    ])


def renew_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="back:plans")],
    ])
