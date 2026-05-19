from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import Subscription, User, async_session_factory
from bot.keyboards import renew_keyboard

router = Router()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("Пользователь не найден. Введите /start")
            return

        sub_result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id, Subscription.is_active == True)
            .order_by(Subscription.expires_at.desc())
        )
        subscription = sub_result.scalar_one_or_none()

    name = user.first_name or "—"
    username = f"@{user.username}" if user.username else "—"
    email = user.email or "не указан"

    if subscription:
        now = datetime.utcnow()
        days_left = (subscription.expires_at - now).days
        expires_str = subscription.expires_at.strftime("%d.%m.%Y")
        sub_text = (
            f"✅ <b>Активна</b>\n"
            f"Тариф: <b>{_plan_name(subscription.plan_key)}</b>\n"
            f"Действует до: <b>{expires_str}</b>\n"
            f"Осталось дней: <b>{max(days_left, 0)}</b>"
        )
        kb = renew_keyboard()
    else:
        sub_text = "❌ <b>Нет активной подписки</b>"
        kb = renew_keyboard()

    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"Имя: {name}\n"
        f"Username: {username}\n"
        f"Email: {email}\n\n"
        f"📋 <b>Подписка</b>\n{sub_text}",
        reply_markup=kb,
    )


def _plan_name(plan_key: str) -> str:
    names = {"1m": "1 месяц"}
    return names.get(plan_key, plan_key)
