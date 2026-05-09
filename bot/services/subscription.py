from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from sqlalchemy import select

from bot.config import PLANS, config
from bot.database import Payment, Subscription, async_session_factory


async def activate_subscription(
    user_id: int,
    telegram_id: int,
    plan_key: str,
    yukassa_payment_id: Optional[str],
    bot: Bot,
    manual: bool = False,
) -> None:
    plan = PLANS[plan_key]
    now = datetime.utcnow()

    async with async_session_factory() as session:
        # Check if there's already an active subscription to extend
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.is_active == True)
            .order_by(Subscription.expires_at.desc())
        )
        existing = result.scalar_one_or_none()

        if existing and existing.expires_at > now:
            # Extend from current expiry
            base = existing.expires_at
        else:
            base = now

        expires_at = base + timedelta(days=30 * plan["months"])

        # Deactivate old subscription
        if existing:
            existing.is_active = False

        # Create new subscription
        sub = Subscription(
            user_id=user_id,
            plan_key=plan_key,
            started_at=now,
            expires_at=expires_at,
            is_active=True,
        )
        session.add(sub)

        # Update payment status if not manual
        if yukassa_payment_id:
            pay_result = await session.execute(
                select(Payment).where(Payment.yukassa_payment_id == yukassa_payment_id)
            )
            payment = pay_result.scalar_one_or_none()
            if payment:
                payment.status = "succeeded"

        await session.commit()

    # Grant channel access via invite link
    expires_str = expires_at.strftime("%d.%m.%Y")
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=config.CHANNEL_ID,
            member_limit=1,
            name=f"sub_{user_id}",
        )
        source = "вручную администратором" if manual else f"за тариф «{plan['name']}»"
        await bot.send_message(
            telegram_id,
            f"✅ <b>Доступ выдан!</b>\n\n"
            f"Тариф: <b>{plan['name']}</b> ({source})\n"
            f"Действует до: <b>{expires_str}</b>\n\n"
            f"Ваша ссылка на закрытый канал (одноразовая):\n{invite.invite_link}",
        )
    except Exception as e:
        await bot.send_message(
            telegram_id,
            f"✅ <b>Подписка активирована</b> до {expires_str}.\n\n"
            "Не удалось автоматически создать ссылку на канал — обратитесь в поддержку.",
        )


async def revoke_subscription(user_id: int, telegram_id: int, bot: Bot) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.is_active == True)
        )
        subscriptions = result.scalars().all()
        for sub in subscriptions:
            sub.is_active = False
        await session.commit()

    # Remove from channel
    try:
        await bot.ban_chat_member(config.CHANNEL_ID, telegram_id)
        await bot.unban_chat_member(config.CHANNEL_ID, telegram_id)
    except Exception:
        pass

    try:
        await bot.send_message(
            telegram_id,
            "ℹ️ Ваша подписка была отозвана администратором. "
            "Если это ошибка — обратитесь в поддержку.",
        )
    except Exception:
        pass
