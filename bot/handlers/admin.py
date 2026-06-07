from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, func, select

from bot.config import PLANS, config
from bot.database import Payment, Subscription, User, async_session_factory
from bot.keyboards import (
    admin_panel_keyboard,
    admin_plan_keyboard,
    confirm_broadcast_keyboard,
    resident_application_keyboard,
)
from bot.services.subscription import activate_subscription, revoke_subscription
from bot.states import AdminBroadcast, AdminDelete, AdminGrant

router = Router()

ADMIN_ONLY = F.from_user.id.in_(config.ADMIN_IDS)


@router.message(ADMIN_ONLY, F.text == "🔧 Админ-панель")
async def admin_panel(message: Message) -> None:
    await message.answer("🔧 <b>Админ-панель</b>", reply_markup=admin_panel_keyboard())


# ─── Subscribers list ────────────────────────────────────────────────────────

@router.callback_query(ADMIN_ONLY, F.data == "admin:users")
async def admin_users(callback: CallbackQuery) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User, Subscription)
            .outerjoin(
                Subscription,
                (Subscription.user_id == User.id) & (Subscription.is_active == True),
            )
            .order_by(User.created_at.desc())
            .limit(50)
        )
        rows = result.all()

    if not rows:
        await callback.message.edit_text("Пользователей пока нет.", reply_markup=admin_panel_keyboard())
        return

    lines = ["👥 <b>Пользователи (последние 50)</b>\n"]
    for user, sub in rows:
        name = user.first_name or "—"
        un = f"@{user.username}" if user.username else "—"
        if sub:
            exp = sub.expires_at.strftime("%d.%m.%Y")
            status = f"✅ до {exp}"
        else:
            status = "❌ нет"
        lines.append(f"• {name} ({un}) <code>{user.telegram_id}</code> — {status}")

    await callback.message.edit_text("\n".join(lines), reply_markup=admin_panel_keyboard())


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.callback_query(ADMIN_ONLY, F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    async with async_session_factory() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar()
        active_subs = (await session.execute(
            select(func.count(Subscription.id)).where(Subscription.is_active == True)
        )).scalar()
        total_revenue = (await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "succeeded")
        )).scalar() or 0

        plan_stats = []
        for key in PLANS:
            count = (await session.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.plan_key == key,
                    Subscription.is_active == True,
                )
            )).scalar()
            plan_stats.append(f"  {PLANS[key]['name']}: {count}")

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"✅ Активных подписок: <b>{active_subs}</b>\n"
        f"💰 Общая выручка: <b>{int(total_revenue):,} ₽</b>\n\n".replace(",", " ") +
        "<b>По тарифам (активные):</b>\n" + "\n".join(plan_stats)
    )
    await callback.message.edit_text(text, reply_markup=admin_panel_keyboard())


# ─── Manual grant ─────────────────────────────────────────────────────────────

@router.callback_query(ADMIN_ONLY, F.data == "admin:grant")
async def admin_grant_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(action="grant")
    await callback.message.edit_text(
        "Введите <b>Telegram ID</b> пользователя, которому хотите выдать подписку:"
    )
    await state.set_state(AdminGrant.waiting_user_id)


@router.message(ADMIN_ONLY, AdminGrant.waiting_user_id)
async def admin_user_id_input(message: Message, state: FSMContext) -> None:
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой Telegram ID:")
        return

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

    if not user:
        await message.answer(f"Пользователь с ID {tg_id} не найден в базе. Введите /start для отмены.")
        return

    data = await state.get_data()
    action = data.get("action", "grant")

    if action == "revoke":
        bot: Bot = message.bot
        await revoke_subscription(user_id=user.id, telegram_id=tg_id, bot=bot)
        await state.clear()
        await message.answer(
            f"✅ Подписка пользователя (tg_id: {tg_id}) отозвана.",
            reply_markup=admin_panel_keyboard(),
        )
    else:
        await state.update_data(target_user_id=user.id, target_tg_id=tg_id)
        name = user.first_name or str(tg_id)
        await message.answer(
            f"Пользователь: <b>{name}</b> (id: {tg_id})\nВыберите тариф:",
            reply_markup=admin_plan_keyboard(),
        )
        await state.set_state(AdminGrant.waiting_plan)


@router.callback_query(ADMIN_ONLY, AdminGrant.waiting_plan, F.data.startswith("admin_plan:"))
async def admin_grant_plan(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    plan_key = callback.data.split(":")[1]
    data = await state.get_data()
    user_id = data["target_user_id"]
    tg_id = data["target_tg_id"]

    await activate_subscription(
        user_id=user_id,
        telegram_id=tg_id,
        plan_key=plan_key,
        yukassa_payment_id=None,
        bot=bot,
        manual=True,
    )
    await state.clear()
    await callback.message.edit_text(
        f"✅ Подписка <b>{PLANS[plan_key]['name']}</b> выдана пользователю (tg_id: {tg_id}).",
        reply_markup=admin_panel_keyboard(),
    )


# ─── Manual revoke ────────────────────────────────────────────────────────────

@router.callback_query(ADMIN_ONLY, F.data == "admin:revoke")
async def admin_revoke_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(action="revoke")
    await callback.message.edit_text(
        "Введите <b>Telegram ID</b> пользователя, у которого нужно отозвать подписку:"
    )
    await state.set_state(AdminGrant.waiting_user_id)


# ─── Broadcast ────────────────────────────────────────────────────────────────

@router.callback_query(ADMIN_ONLY, F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\nВведите текст сообщения (HTML-форматирование поддерживается):"
    )
    await state.set_state(AdminBroadcast.waiting_text)


@router.message(ADMIN_ONLY, AdminBroadcast.waiting_text)
async def admin_broadcast_text(message: Message, state: FSMContext) -> None:
    await state.update_data(broadcast_text=message.html_text)
    await message.answer(
        f"<b>Предпросмотр:</b>\n\n{message.html_text}\n\n"
        "Отправить всем активным подписчикам?",
        reply_markup=confirm_broadcast_keyboard(),
    )
    await state.set_state(AdminBroadcast.confirm)


@router.callback_query(ADMIN_ONLY, AdminBroadcast.confirm, F.data == "broadcast:confirm")
async def admin_broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await state.clear()

    async with async_session_factory() as session:
        result = await session.execute(
            select(User)
            .join(Subscription, (Subscription.user_id == User.id) & (Subscription.is_active == True))
        )
        users = result.scalars().all()

    sent = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await callback.message.edit_text(
        f"✅ Рассылка завершена.\n\nОтправлено: {sent}\nОшибок: {failed}",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(ADMIN_ONLY, AdminBroadcast.confirm, F.data == "broadcast:cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.", reply_markup=admin_panel_keyboard())


# ─── Delete user ──────────────────────────────────────────────────────────────

@router.callback_query(ADMIN_ONLY, F.data == "admin:delete")
async def admin_delete_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Введите <b>Telegram ID</b> пользователя, которого нужно удалить из базы:\n\n"
        "<i>После удаления пользователь сможет заново зарегистрироваться через /start.</i>"
    )
    await state.set_state(AdminDelete.waiting_user_id)


@router.message(ADMIN_ONLY, AdminDelete.waiting_user_id)
async def admin_delete_user(message: Message, state: FSMContext) -> None:
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите числовой Telegram ID:")
        return

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                f"Пользователь с Telegram ID {tg_id} не найден в базе.",
                reply_markup=admin_panel_keyboard(),
            )
            await state.clear()
            return

        user_name = user.first_name or str(tg_id)
        await session.execute(delete(Payment).where(Payment.user_id == user.id))
        await session.execute(delete(Subscription).where(Subscription.user_id == user.id))
        await session.delete(user)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Пользователь <b>{user_name}</b> (tg_id: {tg_id}) удалён из базы.\n"
        "Теперь он может заново пройти регистрацию через /start.",
        reply_markup=admin_panel_keyboard(),
    )


# ─── Resident application actions ────────────────────────────────────────────

@router.callback_query(ADMIN_ONLY, F.data.startswith("res_grant:"))
async def resident_grant(callback: CallbackQuery, bot: Bot) -> None:
    from bot.keyboards import pay_participant_keyboard
    tg_id = int(callback.data.split(":")[1])

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

    if not user:
        await callback.answer("Пользователь не найден в базе.", show_alert=True)
        return

    try:
        await bot.send_message(
            tg_id,
            "🎉 <b>Ваша заявка одобрена!</b>\n\n"
            "Добро пожаловать в клуб осознанного развития.\n"
            "Для получения доступа оплати подписку:",
            reply_markup=pay_participant_keyboard(),
        )
    except Exception:
        await callback.answer("Не удалось отправить сообщение пользователю.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ Резиденту <b>{user.first_name or tg_id}</b> (<code>{tg_id}</code>) отправлена ссылка на оплату."
    )
    await callback.answer()


@router.callback_query(ADMIN_ONLY, F.data.startswith("res_reject:"))
async def resident_reject(callback: CallbackQuery, bot: Bot) -> None:
    tg_id = int(callback.data.split(":")[1])

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.role = None
            await session.commit()

    try:
        await bot.send_message(
            tg_id,
            "К сожалению, ваша заявка на статус резидента не была одобрена. "
            "Если у вас есть вопросы — обратитесь в поддержку.",
        )
    except Exception:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Заявка резидента <code>{tg_id}</code> отклонена. Пользователь уведомлён.")
    await callback.answer()
