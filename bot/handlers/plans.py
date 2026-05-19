from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards import pay_button

router = Router()

PLANS_TEXT = (
    "📋 <b>Подписка клуба</b>\n\n"
    "Стоимость — <b>2 499 ₽/мес.</b>\n\n"
    "Нажмите «Оплатить», чтобы получить доступ к закрытому сообществу."
)


@router.message(F.text == "📋 Тарифы")
async def show_plans(message: Message) -> None:
    await message.answer(PLANS_TEXT, reply_markup=pay_button("1m"))


@router.callback_query(F.data == "back:plans")
async def back_to_plans(callback: CallbackQuery) -> None:
    await callback.message.edit_text(PLANS_TEXT, reply_markup=pay_button("1m"))
