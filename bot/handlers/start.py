from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.database import User, async_session_factory
from bot.keyboards import admin_menu, main_menu, plans_keyboard, remove_keyboard
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
        await message.answer_photo(
            photo="files/main.jpg",
            caption=f'<b>Привет!</b> <i>Я бот клуба осознанного развития для фрилансеров.\n</i>\n<b>Здесь ты найдёшь:</b>\n• регулярные вебинары и шторм-созвоны;\n• челленджи по продуктивности и ЗОЖ;\n• сообщество единомышленников;\n• эксклюзивные бонусы и встречи;\n• рост в своей нише и повышение навыков.\n\n<b>Выбери, кто ты:</b>\n<tg-emoji emoji-id="5969639928781344216">1️⃣</tg-emoji>Резидент клуба — эксперт, готовый делиться опытом и участвовать в развитии сообщества.\n<tg-emoji emoji-id="5969956094208904688">2️⃣</tg-emoji>Участник клуба — фрилансер, который хочет развиваться и получать новые знания.',
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

    await state.set_state(Registration.waiting_role)
    await message.answer(
        f"✅ Email <b>{email}</b> сохранён!\n\n"
        "Теперь выберите свою роль в клубе:\n\n"
        "1️⃣ Резидент клуба — эксперт, готовый делиться опытом\n"
        "2️⃣ Участник клуба — фрилансер, который хочет развиваться\n\n"
        "Отправьте цифру 1 или 2.",
    )


@router.message(Registration.waiting_role)
async def process_role(message: Message, state: FSMContext) -> None:
    role = message.text.strip().lower()
    if role in ["1", "резидент", "рез"]:
        await message.answer_photo(
            photo="files/rezidents.jpg",
            caption='<tg-emoji emoji-id="5208446014532368627">😍</tg-emoji><b>Отлично! </b>Резиденты получают дополнительные возможности:\n• выступать на вебинарах как эксперты;\n• вести тематические мини‑курсы;\n• получать повышенный статус в чате.\n• участвовать в закрытых встречах с основателем.\n\n<tg-emoji emoji-id="5314268339348972871">✔️</tg-emoji>Заполни короткую анкету, чтобы мы узнали о тебе побольше:\n\n<b>Анкета:</b>\nИмя и фамилия.\nПрофессия/специализация (дизайнер, копирайтер и т.\u200aд.).\nОпыт работы в профессии (лет).\nЧем можешь быть полезен клубу? (кратко: «могу провести мастер‑класс по тайм‑менеджменту», «готов консультировать по маркетингу» и т.\u200aп.).\nКонтакты для связи (Telegram, email).\nРабочая соцсеть: \n\n<b>После заполнения:\n</b>\n<b>Спасибо!</b> Мы рассмотрим твою заявку в течение 2 рабочих дней. Если всё ок — пришлём ссылку на оплату подписки и доступ в клуб<tg-emoji emoji-id="6141104356201602080">💪</tg-emoji>',
        )
    elif role in ["2", "участник", "уч"]:
        await message.answer(
            '<b>Здорово, что ты с нами!</b><tg-emoji emoji-id="5330356071364046086">🤩</tg-emoji>Участники получают:\n• доступ ко всем вебинарам и материалам;\n• участие в челленджах;\n• общение в закрытом чате;\n• скидки от партнёров;\n• всестороннее развитие от кураторов и основателя;\n• возможность повышения квалификации.\n\n<b>Для вступления в клуб оплати подписку:</b>\n<b>Кнопка:</b> «Оплатить подписку».\n<b>Шаг 3. Оплата подписки</b>\n<b>Сообщение бота </b>\nСтоимость подписки — 2\xa0499\xa0руб./мес.\nВыбери способ оплаты:\n• карта (через платёжный шлюз);\n• СБП;\n• Telegram Premium Bot (если подключено).',
            reply_markup=plans_keyboard(),
        )
    else:
        await message.answer("Пожалуйста, отправьте 1 для резидента или 2 для участника.")
        return

    await state.clear()
