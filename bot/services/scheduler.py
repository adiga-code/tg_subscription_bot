from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from bot.database import Subscription, User, async_session_factory
from bot.services.subscription import revoke_subscription


async def check_subscriptions(bot: Bot) -> None:
    now = datetime.utcnow()
    reminder_threshold = now + timedelta(days=3)

    async with async_session_factory() as session:
        # Fetch all active subscriptions with user info
        result = await session.execute(
            select(Subscription, User)
            .join(User, User.id == Subscription.user_id)
            .where(Subscription.is_active == True)
        )
        rows = result.all()

    for sub, user in rows:
        # Expired
        if sub.expires_at <= now:
            await revoke_subscription(user_id=user.id, telegram_id=user.telegram_id, bot=bot)
            try:
                await bot.send_message(
                    user.telegram_id,
                    "⏰ Срок вашей подписки истёк.\n\n"
                    "Чтобы продолжить пользоваться сообществом — "
                    "оформите новую подписку через раздел «Тарифы».",
                )
            except Exception:
                pass

        # Reminder: expires within 3 days and reminder not yet sent
        elif sub.expires_at <= reminder_threshold and not sub.reminded:
            expires_str = sub.expires_at.strftime("%d.%m.%Y")
            try:
                await bot.send_message(
                    user.telegram_id,
                    f"⚠️ <b>Подписка заканчивается!</b>\n\n"
                    f"Срок действия вашей подписки истекает <b>{expires_str}</b>.\n\n"
                    "Продлите подписку в разделе «Тарифы», чтобы не потерять доступ.",
                )
                # Mark reminder as sent
                async with async_session_factory() as session2:
                    result2 = await session2.execute(
                        select(Subscription).where(Subscription.id == sub.id)
                    )
                    s = result2.scalar_one_or_none()
                    if s:
                        s.reminded = True
                        await session2.commit()
            except Exception:
                pass


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_subscriptions,
        trigger="cron",
        hour=9,
        minute=0,
        kwargs={"bot": bot},
    )
    scheduler.start()
    return scheduler
