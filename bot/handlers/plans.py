from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.database import User, async_session_factory
from bot.keyboards import pay_button

router = Router()


def _plans_text(role: str | None) -> str:
    if role == "resident":
        return (
            "📋 <b>Подписка резидента</b>\n\n"
            "Стоимость — <b>2 499 ₽/мес.</b>\n\n"
            "Нажмите «Оплатить», чтобы получить доступ к закрытому сообществу."
        )
    return (
        "📋 <b>Подписка участника</b>\n\n"
        "Стоимость — <b>2 499 ₽/мес.</b>\n\n"
        "Нажмите «Оплатить», чтобы получить доступ к закрытому сообществу."
    )


async def _get_role(tg_id: int) -> str | None:
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        return user.role if user else None


@router.message(F.text == "📋 Тарифы")
async def show_plans(message: Message) -> None:
    role = await _get_role(message.from_user.id)
    await message.answer(_plans_text(role), reply_markup=pay_button("1m"))


@router.callback_query(F.data == "back:plans")
async def back_to_plans(callback: CallbackQuery) -> None:
    role = await _get_role(callback.from_user.id)
    await callback.message.edit_text(_plans_text(role), reply_markup=pay_button("1m"))
    await callback.answer()
