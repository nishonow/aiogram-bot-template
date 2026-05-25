"""Entry point and main-menu navigation."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.states import Admin

router = Router(name="admin_main")


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


@router.message(Admin.main, F.text == T.BTN_EXIT)
async def exit_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(T.MSG_EXIT, reply_markup=kb.remove_kb())
