from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.database import User, async_session_factory
from bot.keyboards import admin_menu, main_menu, remove_keyboard
from bot.states import Registration

router = Router()


async def get_or_create_user(tg_id: int, username: str | None, first_name: str | None, last_name: str | None) -> User:
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=tg_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=tg_id in config.ADMIN_IDS,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Update name/username in case they changed
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            await session.commit()
        return user


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()

    user = await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    name = message.from_user.first_name or "друг"

    if not user.email:
        await message.answer(
            f"👋 Привет, <b>{name}</b>!\n\n"
            "Добро пожаловать в бот подписки.\n\n"
            "Для начала введите ваш <b>email</b> — он нужен для отправки чека об оплате:",
            reply_markup=remove_keyboard(),
        )
        await state.set_state(Registration.waiting_email)
    else:
        kb = admin_menu() if user.is_admin else main_menu()
        await message.answer(
            f"👋 С возвращением, <b>{name}</b>!\n\n"
            "Выберите раздел:",
            reply_markup=kb,
        )


@router.message(Registration.waiting_email)
async def process_email(message: Message, state: FSMContext) -> None:
    email = message.text.strip().lower()

    # Basic email validation
    if "@" not in email or "." not in email.split("@")[-1]:
        await message.answer("Пожалуйста, введите корректный email:")
        return

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user:
            user.email = email
            await session.commit()

    await state.clear()

    kb = admin_menu() if message.from_user.id in config.ADMIN_IDS else main_menu()
    await message.answer(
        f"✅ Email <b>{email}</b> сохранён!\n\n"
        "Теперь вы можете ознакомиться с тарифами и оформить подписку.",
        reply_markup=kb,
    )
