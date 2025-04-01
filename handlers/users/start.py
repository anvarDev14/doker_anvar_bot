# handlers/users/start.py
from aiogram.dispatcher.filters import CommandStart
from googletrans import Translator
from dotenv import load_dotenv
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import requests
from loader import bot, dp

# .env faylidan ma'lumotlarni yuklash
load_dotenv()

# Translator obyektini yaratish
translator = Translator()

# Valyuta konvertatsiyasi uchun holatlar
class CurrencyStates(StatesGroup):
    waiting_for_amount = State()

# Start komandasi uchun handler
@dp.message_handler(CommandStart())
async def start_message(message: types.Message):
    await message.answer(f"Assalomu aleykum {message.from_user.full_name}!\n"
                         f"Matn kiriting, men uni siz tanlagan tilga tarjima qilaman.\n"
                         f"Valyuta konvertatsiyasi uchun /valyuta ni bosing.")

# Valyuta komandasi uchun handler
@dp.message_handler(commands="valyuta")
async def currency_function(message: types.Message):
    # Inline tugmalar bilan valyuta tanlash (bayroqlar qo'shilgan)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🇺🇸 USD", callback_data="currency_USD"),
        InlineKeyboardButton("🇪🇺 EUR", callback_data="currency_EUR"),
        InlineKeyboardButton("🇷🇺 RUB", callback_data="currency_RUB")
    )
    keyboard.add(
        InlineKeyboardButton("🇬🇧 GBP", callback_data="currency_GBP"),
        InlineKeyboardButton("🇯🇵 JPY", callback_data="currency_JPY")
    )
    await message.answer("Konvertatsiya qilmoqchi bo'lgan valyutani tanlang:", reply_markup=keyboard)

# Valyuta tanlanganda ishlaydigan handler
@dp.callback_query_handler(lambda c: c.data.startswith("currency_"))
async def process_currency_choice(callback_query: types.CallbackQuery, state: FSMContext):
    currency = callback_query.data.split("_")[1]  # Tanlangan valyuta (masalan, USD)

    # Valyuta kursini olish
    url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
    response = requests.get(url).json()

    # Tanlangan valyuta kursini topish
    rate = None
    for curr in response:
        if curr['Ccy'] == currency:
            rate = float(curr['Rate'])
            break

    # Tanlangan valyutani saqlash
    await state.update_data(chosen_currency=currency)

    # Foydalanuvchiga kurs haqida ma'lumot va summa kiritishni so'rash
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"1 {currency} = {rate} so'm\n"
             f"{currency} ga konvertatsiya qilish uchun so'mda summarni kiriting:",
        reply_markup=None
    )
    await CurrencyStates.waiting_for_amount.set()  # Summa kiritish holatiga o'tish
    await callback_query.answer()

# Summa kiritilganda ishlaydigan handler
@dp.message_handler(state=CurrencyStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)  # Kiritilgan summanni float ga aylantirish
        user_data = await state.get_data()
        chosen_currency = user_data['chosen_currency']

        # Valyuta kursini olish
        url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
        response = requests.get(url).json()

        # Tanlangan valyuta kursini topish
        for currency in response:
            if currency['Ccy'] == chosen_currency:
                rate = float(currency['Rate'])
                result = amount / rate  # Konvertatsiya
                await message.answer(f"{amount} so'm = {result:.2f} {chosen_currency}")
                break

        await state.finish()  # Holatni yakunlash
    except ValueError:
        await message.answer("Iltimos, to'g'ri summa kiriting (masalan, 10000).")
    except Exception as e:
        await message.answer("Xatolik yuz berdi, qaytadan urinib ko'ring.")
        await state.finish()

# Foydalanuvchi xabar yuborganida ishlaydigan handler (faqat komandasiz matnlar uchun)
@dp.message_handler(lambda message: not message.text.startswith('/'))
async def translate_message(message: types.Message):
    # Inline tugmalar yaratish (bayroqlar qo'shilgan)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Uzbekcha 🇺🇿", callback_data=f"uz_{message.message_id}"),
        InlineKeyboardButton("Ruscha 🇷🇺", callback_data=f"ru_{message.message_id}"),
        InlineKeyboardButton("English 🇬🇧", callback_data=f"en_{message.message_id}")
    )

    # Foydalanuvchiga xabar va tugmalar yuborish
    await message.reply(f"Sizning matningiz: {message.text}\n"
                        f"Tarjima uchun tilni tanlang:", reply_markup=keyboard)

# Inline tugma bosilganda ishlaydigan handler (tarjima uchun)
@dp.callback_query_handler(lambda c: c.data.startswith(('uz', 'ru', 'en')))
async def process_callback(callback_query: types.CallbackQuery):
    lang, message_id = callback_query.data.split('_')
    original_message = callback_query.message.reply_to_message.text

    # Tarjima qilish
    tr = translator.translate(original_message, dest=lang)
    translated_text = tr.text

    # Tarjima natijasini yuborish va tugmalarni o'chirish
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Tarjima ({lang}):\n{translated_text}",
        reply_markup=None
    )
    await callback_query.answer()

# Botni ishga tushirish (agar bu fayl asosiy fayl bo'lmasa, bu qism o'chiriladi)
# if __name__ == '__main__':
#     executor.start_polling(dp, skip_updates=True)