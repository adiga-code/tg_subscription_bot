from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy import select

from bot.config import config
from bot.database import User, async_session_factory
from bot.keyboards import (
    admin_menu,
    main_menu,
    pay_participant_keyboard,
    resident_application_keyboard,
    role_selection_keyboard,
)
from bot.states import ResidentQuestionnaire

router = Router()


async def get_or_create_user(
    tg_id: int, username: str | None, first_name: str | None, last_name: str | None
) -> User:
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

    if user.role is None:
        await message.answer_photo(
            photo=FSInputFile("files/main.jpg"),
            caption=(
                "<b>Привет!</b> <i>Я бот клуба осознанного развития для фрилансеров.\n</i>\n"
                "<b>Здесь ты найдёшь:</b>\n"
                "• регулярные вебинары и мастер‑классы;\n"
                "• челленджи по продуктивности и ЗОЖ;\n"
                "• сообщество единомышленников;\n"
                "• эксклюзивные бонусы и скидки.\n\n"
                "<b>Выбери, кто ты:</b>\n"
                '<tg-emoji emoji-id="5969639928781344216">1️⃣</tg-emoji>'
                "Резидент клуба — эксперт, готовый делиться опытом и участвовать в развитии сообщества.\n"
                '<tg-emoji emoji-id="5969956094208904688">2️⃣</tg-emoji>'
                "Участник клуба — фрилансер, который хочет развиваться и получать новые знания."
            ),
            reply_markup=role_selection_keyboard(),
        )
    else:
        kb = admin_menu() if user.is_admin else main_menu()
        await message.answer(
            f"👋 С возвращением, <b>{name}</b>!\n\nВыберите раздел:",
            reply_markup=kb,
        )


# ─── Role selection callbacks ─────────────────────────────────────────────────

@router.callback_query(F.data == "role:resident")
async def choose_resident(callback: CallbackQuery, state: FSMContext) -> None:
    tg_id = callback.from_user.id

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.role = "resident"
            await session.commit()

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=FSInputFile("files/rezidents.jpg"),
        caption=(
            '<tg-emoji emoji-id="5208446014532368627">😍</tg-emoji><b>Отлично! </b>'
            "Резиденты получают дополнительные возможности:\n"
            "• выступать на вебинарах как эксперты;\n"
            "• вести тематические мини‑курсы;\n"
            "• получать повышенный статус в чате;\n"
            "• участвовать в закрытых встречах с основателем.\n\n"
            '<tg-emoji emoji-id="5314268339348972871">✔️</tg-emoji>'
            "Заполни короткую анкету, чтобы мы узнали о тебе побольше:"
        ),
    )
    await callback.message.answer("Введите ваше <b>имя и фамилию</b>:")
    await state.set_state(ResidentQuestionnaire.waiting_name)
    await callback.answer()


@router.callback_query(F.data == "role:participant")
async def choose_participant(callback: CallbackQuery) -> None:
    tg_id = callback.from_user.id

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.role = "participant"
            await session.commit()

    await callback.message.delete()
    await callback.message.answer(
        '<b>Здорово, что ты с нами!</b><tg-emoji emoji-id="5330356071364046086">🤩</tg-emoji> '
        "Участники получают:\n"
        "• доступ ко всем вебинарам и материалам;\n"
        "• участие в челленджах;\n"
        "• общение в закрытом чате;\n"
        "• скидки от партнёров;\n"
        "• всестороннее развитие от кураторов и основателя;\n"
        "• возможность повышения квалификации.\n\n"
        "<b>Для вступления в клуб оплати подписку:</b>",
        reply_markup=pay_participant_keyboard(),
    )
    await callback.answer()


# ─── Resident questionnaire ───────────────────────────────────────────────────

@router.message(ResidentQuestionnaire.waiting_name)
async def questionnaire_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await message.answer("Укажите вашу <b>профессию/специализацию</b> (дизайнер, копирайтер и т. д.):")
    await state.set_state(ResidentQuestionnaire.waiting_profession)


@router.message(ResidentQuestionnaire.waiting_profession)
async def questionnaire_profession(message: Message, state: FSMContext) -> None:
    await state.update_data(profession=message.text.strip())
    await message.answer("Ваш <b>опыт работы</b> в профессии (лет):")
    await state.set_state(ResidentQuestionnaire.waiting_experience)


@router.message(ResidentQuestionnaire.waiting_experience)
async def questionnaire_experience(message: Message, state: FSMContext) -> None:
    await state.update_data(experience=message.text.strip())
    await message.answer(
        "<b>Чем можете быть полезны клубу?</b>\n"
        "<i>Кратко: «могу провести мастер‑класс по тайм‑менеджменту», «готов консультировать по маркетингу» и т. п.</i>"
    )
    await state.set_state(ResidentQuestionnaire.waiting_value)


@router.message(ResidentQuestionnaire.waiting_value)
async def questionnaire_value(message: Message, state: FSMContext) -> None:
    await state.update_data(value=message.text.strip())
    await message.answer("<b>Контакты для связи</b> (Telegram, email):")
    await state.set_state(ResidentQuestionnaire.waiting_contacts)


@router.message(ResidentQuestionnaire.waiting_contacts)
async def questionnaire_contacts(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(contacts=message.text.strip())
    data = await state.get_data()
    await state.clear()

    # Notify admins
    username = f"@{message.from_user.username}" if message.from_user.username else f"id:{message.from_user.id}"
    admin_text = (
        "📋 <b>Новая заявка резидента</b>\n\n"
        f"👤 {username} (tg_id: {message.from_user.id})\n"
        f"Имя: {data.get('name', '—')}\n"
        f"Профессия: {data.get('profession', '—')}\n"
        f"Опыт: {data.get('experience', '—')} лет\n"
        f"Польза для клуба: {data.get('value', '—')}\n"
        f"Контакты: {data.get('contacts', '—')}"
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=resident_application_keyboard(message.from_user.id),
            )
        except Exception:
            pass

    await message.answer(
        "<b>Спасибо!</b> Мы рассмотрим твою заявку в течение 2 рабочих дней. "
        "Если всё ок — пришлём ссылку на оплату подписки и доступ в клуб"
        '<tg-emoji emoji-id="6141104356201602080">💪</tg-emoji>'
    )
