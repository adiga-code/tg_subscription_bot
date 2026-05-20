from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards import pay_button, role_selection_keyboard

router = Router()

ROLE_SELECT_TEXT = (
    "📋 <b>Вступление в клуб</b>\n\n"
    "Выбери, кто ты:\n\n"
    "1️⃣ <b>Резидент</b> — эксперт, готовый делиться опытом и участвовать в развитии сообщества.\n"
    "2️⃣ <b>Участник</b> — фрилансер, который хочет развиваться и получать новые знания.\n\n"
    "Стоимость подписки — <b>2 499 ₽/мес.</b>"
)

PLANS_TEXT = (
    "📋 <b>Подписка клуба</b>\n\n"
    "Стоимость — <b>2 499 ₽/мес.</b>\n\n"
    "Нажмите «Оплатить», чтобы получить доступ к закрытому сообществу."
)


@router.message(F.text == "📋 Тарифы")
async def show_plans(message: Message) -> None:
    await message.answer(ROLE_SELECT_TEXT, reply_markup=role_selection_keyboard())


@router.callback_query(F.data == "back:plans")
async def back_to_plans(callback: CallbackQuery) -> None:
    await callback.message.edit_text(PLANS_TEXT, reply_markup=pay_button("1m"))
