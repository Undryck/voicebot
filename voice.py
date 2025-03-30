import os
import uuid
import asyncio
import random
import aiohttp
import logging
import sqlite3
from gtts import gTTS
from aiogram.types import InputMediaPhoto, InputMediaVideo
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from pydub import AudioSegment
from pydub.utils import which
import speech_recognition as sr

    # Ініціалізація бота та диспетчера
bot = Bot(token='7988490161:AAE8vX6zGaXeb5LFWUBSbNfR6RCpABUnW9g')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

ADMIN_ID = 5019012143  # ID адміна
TOKEN = '6333120732:AAEqHvLkp6x-2JMmkvgqzGtMSJNRvh4Nc_U'

AudioSegment.converter = which("ffmpeg")

# Підключення до бази даних
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Створюємо таблицю, якщо її немає
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,
    first_name TEXT
)''')
# Створюємо таблицю для збережених голосових повідомлень
cursor.execute('''CREATE TABLE IF NOT EXISTS saved_voices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    short_id TEXT UNIQUE,
    file_id TEXT
)''')
conn.commit()

# Функція додавання користувача
def add_user(user_id, first_name):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
    conn.commit()

# Отримати загальну кількість користувачів
def get_users_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

# Отримати всіх користувачів (тільки для адміна)
def get_all_users():
    cursor.execute("SELECT user_id, first_name FROM users")
    return cursor.fetchall()

# Додає голосове повідомлення у збережені
def save_voice_to_db(user_id, short_id, file_id):
    cursor.execute("INSERT OR IGNORE INTO saved_voices (user_id, short_id, file_id) VALUES (?, ?, ?)",
                   (user_id, short_id, file_id))
    conn.commit()

# Отримує всі збережені голосові для конкретного користувача
def get_saved_voices(user_id):
    cursor.execute("SELECT short_id, file_id FROM saved_voices WHERE user_id=?", (user_id,))
    return cursor.fetchall()

# Отримує file_id голосового за його short_id
def get_voice_file_id(short_id):
    cursor.execute("SELECT file_id FROM saved_voices WHERE short_id=?", (short_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Видаляє голосове повідомлення з бази
def delete_voice_from_db(user_id, short_id):
    cursor.execute("DELETE FROM saved_voices WHERE user_id=? AND short_id=?", (user_id, short_id))
    conn.commit()

class ConvertToVoiceStep(StatesGroup):
        waiting_for_text = State()
        waiting_for_audio = State()

CHANNELS = [
        ["Канал №1", "-1002387051357", "https://t.me/Creatorbotua"],
]

voices = {
    'voice1': ('uk', 'Українська 🇺🇦'),
    'voice2': ('pl', 'Polski 🇵🇱'),
    'voice3': ('it', 'Italiano 🇮🇹'),
    'voice4': ('fr', 'Français 🇫🇷'),
    'voice5': ('en', 'English 🇺🇲'),
    'voice6': ('es', 'Español 🇪🇸')
}

NOT_SUB_MESSAGE = "<b>‼Ви не підписалися на канал!</b>\n\nПідпишіться будь ласка та спробуйте ще раз 🙂"

async def check_sub_channels(channels, user_id):
        for channel in channels:
            chat_member = await bot.get_chat_member(chat_id=channel[1], user_id=user_id)
            if chat_member['status'] == 'left':
                return False
        return True

def showChannels():
        submarkup = InlineKeyboardMarkup(row_width=1)

        for channel in CHANNELS:
            btn = InlineKeyboardButton(text=channel[0], url=channel[2])
            submarkup.insert(btn)

        btndonesub = InlineKeyboardButton(text='🔐Перевірити підписку', callback_data='subchanneldone')
        submarkup.insert(btndonesub)

        return submarkup
@dp.callback_query_handler(text='subchanneldone', state="*")
async def check_subscription(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    if await check_sub_channels(CHANNELS, user_id):
        await state.finish()  # Закінчуємо стан
        await call.message.delete()
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        itembtn2 = KeyboardButton('Конвертація🔊')
        markup.row(itembtn2)
        itembtn1 = KeyboardButton('🗣️Вибрати голос')
        itembtn3 = KeyboardButton('Інструкція📜')
        itembtn4 = KeyboardButton('⭐️Збережене')
        markup.row(itembtn1, itembtn3)
        markup.row(itembtn4)
        markup.add()

        first_name = call.from_user.first_name
        greeting_text = f"Привіт, <b>{first_name}!</b> 😊\n💼 @Voice_text_ua_bot - бот, який вміє конвертувати текст у голос 🎙️\n\nТакож працює у <b>групах</b> та <b>чатах</b>💬\n\n🖇<b>Вміє зберігати потрібні голосові повідомлення\n❗Може озвучувати текст різними мовами та голосами</b>"
        await call.message.answer(greeting_text, parse_mode=types.ParseMode.HTML, reply_markup=markup)
    else:
        await call.message.delete()
        await call.message.answer(NOT_SUB_MESSAGE, parse_mode=types.ParseMode.HTML, reply_markup=showChannels())

class ReklamaStates(StatesGroup):
    waiting_for_ad_text = State()
    waiting_for_media_confirmation = State()
    waiting_for_media = State()
    waiting_for_button_confirmation = State()
    waiting_for_number_of_buttons = State()
    waiting_for_buttons_text = State()
    waiting_for_buttons_url = State()

# Команда для запуску реклами
@dp.message_handler(commands=['reklama'])
async def send_reklama(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("✍ Введіть текст реклами для розсилки:")
        await ReklamaStates.waiting_for_ad_text.set()  # Перехід до стану введення тексту реклами
    else:
        pass

# 2️⃣ Хендлер для очікування тексту реклами
@dp.message_handler(state=ReklamaStates.waiting_for_ad_text)
async def get_ad_text(message: types.Message, state: FSMContext):
    ad_text = message.text
    await state.update_data(ad_text=ad_text)  # Зберігаємо текст реклами в контексті

    # Запитуємо, чи хоче адмін надіслати фото чи відео
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Так, надіслати медіа", callback_data="send_media_yes"),
        InlineKeyboardButton("Ні, продовжити без медіа", callback_data="send_media_no")
    )
    await message.answer("✅ Текст реклами додано. Бажаєте додати фото чи відео?", reply_markup=keyboard)
    await ReklamaStates.waiting_for_media_confirmation.set()  # Перехід до стану підтвердження медіа

@dp.callback_query_handler(lambda c: c.data in ["send_media_yes", "send_media_no"], state=ReklamaStates.waiting_for_media_confirmation)
async def confirm_media(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "send_media_yes":
        await callback_query.message.answer("📸 Надішліть фото чи відео для реклами.")
        await ReklamaStates.waiting_for_media.set()
    else:
        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Так", callback_data="confirm_buttons_yes"),
            InlineKeyboardButton("Ні", callback_data="confirm_buttons_no")
        )
        await callback_query.message.answer("✅ Медіа не буде додано. Додати кнопки?", reply_markup=keyboard)
        await ReklamaStates.waiting_for_button_confirmation.set()

@dp.message_handler(content_types=['photo', 'video'], state=ReklamaStates.waiting_for_media)
async def get_media(message: types.Message, state: FSMContext):
    media_id = message.photo[-1].file_id if message.photo else message.video.file_id
    media_type = "photo" if message.photo else "video"
    await state.update_data(media=media_id, media_type=media_type)
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Так", callback_data="confirm_buttons_yes"),
        InlineKeyboardButton("Ні", callback_data="confirm_buttons_no")
    )
    await message.answer("✅ Медіа додано. Додати кнопки?", reply_markup=keyboard)
    await ReklamaStates.waiting_for_button_confirmation.set()

@dp.callback_query_handler(lambda c: c.data == "confirm_buttons_no", state=ReklamaStates.waiting_for_button_confirmation)
async def send_ad_without_buttons(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    for user_id in users:
        try:
            if 'media' in data:
                if data['media_type'] == "photo":
                    await bot.send_photo(user_id[0], data['media'], caption=data['ad_text'], parse_mode='HTML')
                else:
                    await bot.send_video(user_id[0], data['media'], caption=data['ad_text'], parse_mode='HTML')
            else:
                await bot.send_message(user_id[0], data['ad_text'], parse_mode='HTML')
        except:
            pass
    await callback_query.message.answer("✅ Реклама надіслана всім користувачам.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "confirm_buttons_yes", state=ReklamaStates.waiting_for_button_confirmation)
async def ask_number_of_buttons(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✍ Скільки кнопок потрібно додати? Введіть число:")
    await ReklamaStates.waiting_for_number_of_buttons.set()

# 6️⃣ Хендлер для отримання кількості кнопок
@dp.message_handler(state=ReklamaStates.waiting_for_number_of_buttons)
async def get_number_of_buttons(message: types.Message, state: FSMContext):
    try:
        number_of_buttons = int(message.text)  # Перевіряємо, чи є це числом
        if number_of_buttons <= 0:
            await message.answer("❗ Кількість кнопок має бути більше 0.")
            return
    except ValueError:
        await message.answer("❗ Будь ласка, введіть число.")
        return

    await state.update_data(number_of_buttons=number_of_buttons)  # Зберігаємо кількість кнопок
    await message.answer("✍ Тепер надішліть URL для кнопок:")
    await ReklamaStates.waiting_for_buttons_url.set()

# 7️⃣ Хендлер для отримання URL для кнопок
@dp.message_handler(state=ReklamaStates.waiting_for_buttons_url)
async def get_url_for_buttons(message: types.Message, state: FSMContext):
    url = message.text
    await state.update_data(url_for_buttons=url)  # Зберігаємо URL

    # Запитуємо текст для кожної кнопки
    number_of_buttons = (await state.get_data())['number_of_buttons']
    await message.answer(f"✍ Тепер надішліть текст для кожної з {number_of_buttons} кнопок у форматі:\n"
                         "1 - текст кнопки 1\n"
                         "2 - текст кнопки 2\n"
                         "...\n"
                         "Наприклад: \n1 - Кнопка 1\n2 - Кнопка 2\n3 - Кнопка 3\n4 - Кнопка 4")
    await ReklamaStates.waiting_for_buttons_text.set()

# 8️⃣ Хендлер для отримання текстів кнопок
@dp.message_handler(state=ReklamaStates.waiting_for_buttons_text)
async def get_button_texts(message: types.Message, state: FSMContext):
    button_texts = message.text.split("\n")  # Розділяємо введений текст на окремі рядки
    if len(button_texts) != (await state.get_data())['number_of_buttons']:
        await message.answer(f"❗ Будь ласка, введіть текст для рівно {await state.get_data()['number_of_buttons']} кнопок.")
        return

    # Створюємо список текстів для кнопок
    button_texts = {int(line.split(' - ')[0]): line.split(' - ')[1] for line in button_texts}
    await state.update_data(button_texts=button_texts)  # Зберігаємо тексти кнопок

    ad_text = (await state.get_data())['ad_text']
    number_of_buttons = (await state.get_data())['number_of_buttons']
    url_for_buttons = (await state.get_data())['url_for_buttons']
    media = (await state.get_data()).get('media')

    # Створення inline кнопок з текстами
    keyboard = InlineKeyboardMarkup(row_width=number_of_buttons)
    for i in range(1, number_of_buttons + 1):
        button_label = button_texts.get(i, f"Кнопка {i}")  # Отримуємо текст для кнопки або за замовчуванням
        keyboard.add(InlineKeyboardButton(button_label, url=url_for_buttons))

    # Відправляємо рекламу з кнопками та медіа всім користувачам
    users = get_all_users()
    for user_id in users:
        try:
            if media:
                await bot.send_photo(user_id[0], media, caption=ad_text, parse_mode='HTML', reply_markup=keyboard) if isinstance(media, str) else await bot.send_video(user_id[0], media, caption=ad_text, parse_mode='HTML', reply_markup=keyboard)
            else:
                await bot.send_message(user_id[0], ad_text, parse_mode='HTML', reply_markup=keyboard)
        except Exception as e:
            pass

    await message.answer("✅ Реклама з кнопками та медіа надіслана всім користувачам.")
    await state.finish()

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message, state: FSMContext):
    first_name = message.from_user.first_name  # Додаємо отримання імені користувача
    user_id = message.from_user.id

    add_user(user_id, first_name)

    if message.chat.type == 'private':  # Обробка приватного чату
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        itembtn2 = KeyboardButton('Конвертація🔊')
        markup.row(itembtn2)
        itembtn1 = KeyboardButton('🗣️Вибрати голос')
        itembtn3 = KeyboardButton('Інструкція📜')
        itembtn4 = KeyboardButton('⭐️Збережене')
        markup.row(itembtn1, itembtn3)
        markup.row(itembtn4)
        markup.add()

        greeting_text = f"Привіт, <b>{first_name}!</b> 😊\n💼 @Voice_text_ua_bot - бот, який вміє конвертувати текст у голос 🎙️\n\nТакож працює у <b>групах</b> та <b>чатах</b>💬\n\n🖇<b>Вміє зберігати потрібні голосові повідомлення\n❗Може озвучувати текст різними мовами та голосами</b>"
        await state.finish()
        await message.answer(greeting_text, parse_mode=types.ParseMode.HTML, reply_markup=markup)

    elif message.chat.type in ['group', 'supergroup']:  # Обробка для груп
        greeting_text = f'Привіт, <b>{first_name}!</b> 😊\n💼 Я бот для конвертації тексту у голос 🎙️\n\n<b>Щоб використовувати мої функції у групі:</b>\n✅ Надішліть /voice <i>текст</i> для конвертації\n✅ Використовуйте /lang для вибору мови'
        await message.reply(greeting_text, parse_mode=types.ParseMode.HTML)

@dp.message_handler(commands=['delete'], chat_type='private')
async def delete_saved_voices(message: types.Message):
    user_id = message.from_user.id

    #subscribed = await check_sub_channels(CHANNELS, message.from_user.id)

    #if subscribed:
    
    # Отримуємо всі збережені голосові повідомлення для користувача з бази даних
    saved_voices = get_saved_voices(user_id)

    if not saved_voices:
        await message.answer("<b>📭 Ваш список збережених поки що порожній!</b>\n\n😯 Ви ще не додали жодного голосового файлу в збережене\n\n🔁Тут можна швидко знайти та використати голосовий файл знову без повторної генерації!", parse_mode=types.ParseMode.HTML)
        return

    # Видаляємо всі збережені голосові повідомлення з бази даних
    for short_id, file_id in saved_voices:
        delete_voice_from_db(user_id, short_id)

    await message.answer("Збережене було успішно очищене!📦")

    #else:
       # await message.answer(
            #"<b>Для того щоб отримати доступ до функцій бота, вам потрібно підписатися на канал</b> 👇🏻",
            #parse_mode=types.ParseMode.HTML,
            #reply_markup=showChannels()
        #)

@dp.message_handler(commands=['users'])
async def show_users(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        users = get_all_users()
        count = get_users_count()
        if users:
            text = "\n".join([f"{user[1]} (ID: {user[0]})" for user in users])
            await message.answer(f"{count}\n\n📋 Список користувачів:\n{text}")
        else:
            await message.answer("❌ У базі немає користувачів.")
    else:
        pass

@dp.message_handler(commands=['voice'])
async def convert_command(message: types.Message, state: FSMContext):
        if message.chat.type in ['group', 'supergroup']:
            text = ' '.join(message.text.split()[1:])
            if not text:
                await message.reply("Ви не написали текст.")
            else:
                voice = user_voice.get(message.from_user.id, 'uk')  # default voice
                language = voice.split("-")[0]
                speech = gTTS(text=text, lang=language, slow=False)
                speech.save("speech.ogg")
                audio = open("speech.ogg", "rb")
                await message.reply_audio(audio, caption="@Voice_text_ua_bot")
                os.remove("speech.ogg")

@dp.message_handler(commands=['lang'])
async def voice_command(message: types.Message, state: FSMContext):
        if message.chat.type in ['group', 'supergroup']:
            user_id = message.from_user.id
            lang_code = user_voice.get(user_id, 'uk')  # Отримуємо поточний голос користувача
            lang_name = next((name for code, name in voices.values() if code == lang_code), 'Українська 🇺🇦')

            markup = get_first_page_keyboard()  # Використовуємо оновлену клавіатуру

            await message.reply(
    f"📢 Обирайте <b>мову</b> та <b>голос</b> для зручного використання!\n<b>🔹Активна мова:</b> {lang_name}\n\nВи можете змінити налаштування у будь-який момент ⚙️",
    parse_mode=types.ParseMode.HTML,
    reply_markup=markup
)

user_voice_messages = {}

@dp.message_handler(content_types=['text'])
async def process_message(message: types.Message, state: FSMContext):
    if message.chat.type == 'private':
        #subscribed = await check_sub_channels(CHANNELS, message.from_user.id)

        #if subscribed:
        if message.text == '🗣️Вибрати голос':
            user_id = message.from_user.id
            lang_code = user_voice.get(user_id, 'uk')  # Отримуємо код мови
            lang_name = next((name for code, name in voices.values() if code == lang_code), 'Українська 🇺🇦')

            markup = InlineKeyboardMarkup(row_width=2)
            itembtn1 = InlineKeyboardButton("Українська 🇺🇦", callback_data='voice1')
            itembtn2 = InlineKeyboardButton("Polski 🇵🇱", callback_data='voice2')
            itembtn3 = InlineKeyboardButton("Italiano 🇮🇹", callback_data='voice3')
            itembtn4 = InlineKeyboardButton("Français 🇫🇷", callback_data='voice4')
            hu = InlineKeyboardButton("⬅", callback_data='x52')
            hu1 = InlineKeyboardButton("1/2", callback_data='x3')
            hu2 = InlineKeyboardButton("➡", callback_data='x2')
            markup.add(itembtn1, itembtn2, itembtn3, itembtn4)
            markup.row(hu, hu1, hu2)

            await state.finish()
            await message.answer(
                f"📢 Обирайте <b>мову</b> та <b>голос</b> для зручного використання!\n<b>🔹Активна мова:</b> {lang_name}\n\nВи можете змінити налаштування у будь-який момент ⚙️",
                parse_mode=types.ParseMode.HTML,
                reply_markup=markup
            )

        elif message.text == 'Інструкція📜':
            markups1 = InlineKeyboardMarkup(row_width=2)
            itembtn1 = InlineKeyboardButton("➕Додати бота в чат",
                                            url='https://t.me/Voice_text_ua_bot?startgroup=AddGroup')
            markups1.add(itembtn1)
            await state.finish()
            await message.answer(
                '<b>🤖 Інструкція користування бота у групах:</b>\n\n1. Додайте бота в групу\n2. Зробіть його адміністратором\n\n🎙️Конвертація тексту - /voice <i>текст</i>\n\n🌐Вибір мови,голосу - /lang',
                reply_markup=markups1, parse_mode=types.ParseMode.HTML
            )

        elif message.text == '🔙Меню':
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            itembtn2 = KeyboardButton('Конвертація🔊')
            markup.row(itembtn2)
            itembtn1 = KeyboardButton('🗣️Вибрати голос')
            itembtn3 = KeyboardButton('Інструкція📜')
            itembtn4 = KeyboardButton('⭐️Збережене')
            markup.row(itembtn1, itembtn3)
            markup.row(itembtn4)
            markup.add()

            first_name = message.from_user.first_name  # Додаємо отримання імені користувача

            greeting_text = f"Привіт, <b>{first_name}!</b> 😊\n💼 @Voice_text_ua_bot - бот, який вміє конвертувати текст у голос 🎙️\n\nТакож працює у <b>групах</b> та <b>чатах</b>💬\n\n🖇<b>Вміє зберігати потрібні голосові повідомлення\n❗Може озвучувати текст різними мовами та голосами 🇺🇦</b>"
            await state.finish()
            await message.answer(greeting_text, parse_mode=types.ParseMode.HTML, reply_markup=markup)
            
        elif message.text == '⭐️Збережене':
            user_id = message.from_user.id

            # Отримуємо всі збережені голосові повідомлення для користувача з бази даних
            saved_voices = get_saved_voices(user_id)

            if not saved_voices:
                await message.answer(
                "<b>📭 Ваш список збережених поки що порожній!</b>\n\n😯 Ви ще не додали жодного голосового файлу в збережене\n\n🔁Тут можна швидко знайти та використати голосовий файл знову без повторної генерації!",
                    parse_mode=types.ParseMode.HTML  # Вказуємо, що це HTML форматування
            )
                return

            # Рахуємо кількість збережених голосових
            saved_count = len(saved_voices)

            # Створюємо клавіатуру зі списком збережених голосових
            markup = InlineKeyboardMarkup(row_width=1)
            for index, (short_id, file_id) in enumerate(saved_voices, start=1):
                markup.add(InlineKeyboardButton(f"🎙 Голосове №{index}", callback_data=f"play_{short_id}"))

            await message.answer(f"<b>Ваші збережені голосові повідомлення🎵\n\n🖇 Збережено</b> {saved_count}/10\n\n⚙️Для того щоб очистити збережене є команда - /delete", reply_markup=markup, parse_mode=types.ParseMode.HTML)

        elif message.text == 'Конвертація🔊':
                # Отримуємо поточний стан користувача
            current_state = await state.get_state()

            if current_state == 'ConvertToVoiceStep:waiting_for_text':  # Перевіряємо, чи ми в режимі конвертації
                    # Якщо користувач вже в режимі конвертації, завершуємо його
                await state.finish()
                await message.answer("Режим конвертації завершено. Ви можете вибрати іншу опцію.",
                                        reply_markup=ReplyKeyboardMarkup(
                                            resize_keyboard=True,
                                            keyboard=[
                                                [KeyboardButton('Конвертація🔊')],
                                                [KeyboardButton('🗣️Вибрати голос'), KeyboardButton('Інструкція📜')],
                                                [KeyboardButton('⭐️Збережене')]
                                            ]
                                        ))
            else:
                    # Якщо не в режимі конвертації, активуємо його
                await ConvertToVoiceStep.waiting_for_text.set()
                mainmenu = ReplyKeyboardMarkup(resize_keyboard=True)
                conv1 = KeyboardButton('Текст ➡ голос')
                itemenu = KeyboardButton('🔙Меню')
                mainmenu.row(conv1)
                mainmenu.row(itemenu)
                mainmenu.add()
                await message.answer("Надішліть мені текст, який бажаєте конвертувати в голос", reply_markup=mainmenu)

        #else:
            #await message.answer(
                #"<b>Для того щоб отримати доступ до функцій бота, вам потрібно підписатися на канал</b> 👇🏻",
                #parse_mode=types.ParseMode.HTML,
                #reply_markup=showChannels()
            #)

user_saved_voices = {}  # user_id -> list of short_ids
saved_voice_ids = {}  # short_id -> full Telegram file_id
MAX_SAVED_VOICES = 10  # Ліміт на 10 голосових повідомлень

@dp.message_handler(state=ConvertToVoiceStep.waiting_for_text, content_types=types.ContentTypes.TEXT)
async def convert_to_voice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Перевіряємо підписку перед конвертацією
    #subscribed = await check_sub_channels(CHANNELS, user_id)
    #if not subscribed:
        #await message.answer(
            #"<b>Для того щоб отримати доступ до функцій бота, вам потрібно підписатися на канал</b> 👇🏻",
            #parse_mode=types.ParseMode.HTML,
            #reply_markup=showChannels()
        #)
        #return  # Виходимо з функції, не конвертуючи текст

    text = message.text

    # Вихід із режиму, якщо натиснута кнопка
    if text in ['🗣️Вибрати голос', 'Інструкція📜', '🔙Меню', '⭐️Збережене', 'Конвертація🔊']:
        await state.finish()
        await process_message(message, state)
        return

    # Відправляємо повідомлення "Обробляю ваш запит"
    processing_message = await message.answer("🛠 Обробляю ваш запит, будь ласка, зачекайте...")

    # Асинхронно чекаємо від 3 до 5 секунд
    await asyncio.sleep(random.randint(3, 5))

    # Видаляємо повідомлення "Обробляю ваш запит"
    await bot.delete_message(chat_id=message.chat.id, message_id=processing_message.message_id)

    # Тепер генеруємо голосове повідомлення
    voice = user_voice.get(user_id, 'uk')  # default voice
    language = voice.split("-")[0]
    speech = gTTS(text=text, lang=language, slow=False)
    file_path = f"{uuid.uuid4()}.ogg"
    speech.save(file_path)

    # Відправляємо аудіофайл
    with open(file_path, "rb") as audio:
        sent_message = await message.answer_audio(audio, caption="@Voice_text_ua_bot")

    # Видаляємо тимчасовий файл
    os.remove(file_path)

    # Перевіряємо, чи файл успішно надіслано
    if sent_message.audio:
        telegram_file_id = sent_message.audio.file_id
    elif sent_message.voice:
        telegram_file_id = sent_message.voice.file_id
    else:
        return  # Якщо немає file_id, виходимо з функції

    # Створюємо коротке унікальне ID і зберігаємо file_id
    short_id = str(uuid.uuid4())[:8]
    saved_voice_ids[short_id] = telegram_file_id

    # Додаємо кнопку "⭐ Додати в збережене"
    save_button = InlineKeyboardMarkup()
    save_button.add(InlineKeyboardButton("⭐ Додати в збережене", callback_data=f"save_{short_id}"))

    await sent_message.edit_reply_markup(reply_markup=save_button)

    # Встановлюємо стан для обробки наступних повідомлень
    await ConvertToVoiceStep.waiting_for_text.set()
    
@dp.callback_query_handler(lambda call: call.data.startswith("save_"), state="*")
async def save_voice(call: types.CallbackQuery):
    user_id = call.from_user.id
    short_id = call.data.split("_")[1]

    file_id = get_voice_file_id(short_id)
    if file_id:
        await call.answer("⚠️Голосове вже збережене!")
        return

    saved_voices = get_saved_voices(user_id)

    if len(saved_voices) >= MAX_SAVED_VOICES:
        await call.answer("⚠️Ви використали ліміт збережених!")
        return

    if short_id in [sv[0] for sv in saved_voices]:
        await call.answer("⚠️Голосове вже збережене!")
        return

    # Зберігаємо в базу
    save_voice_to_db(user_id, short_id, saved_voice_ids[short_id])
    await call.answer("➕Успішно додано➕")

@dp.callback_query_handler(lambda call: call.data.startswith("play_"), state="*")
async def send_saved_voice(call: types.CallbackQuery):
    short_id = call.data.split("_")[1]
    file_id = get_voice_file_id(short_id)

    if not file_id:
        await call.answer("❌Це голосове видалене")
        return

    delete_button = types.InlineKeyboardMarkup()
    delete_button.add(types.InlineKeyboardButton("🗑 Видалити", callback_data=f"delete_{short_id}"))

    await call.message.answer_audio(file_id, caption="🎙 Ваше збережене голосове повідомлення", reply_markup=delete_button)

@dp.callback_query_handler(lambda call: call.data.startswith("delete_"), state="*")
async def delete_saved_voice(call: types.CallbackQuery):
    user_id = call.from_user.id
    short_id = call.data.split("_")[1]

    file_id = get_voice_file_id(short_id)

    if file_id:
        delete_voice_from_db(user_id, short_id)
        await call.answer("➖Успішно вилучено➖")
        await call.message.delete()
    else:
        await call.answer("❌ Це голосове видалене")

user_voice = {}

# Список голосів
voices = {
    'voice1': ('uk', 'Українська 🇺🇦'),
    'voice2': ('pl', 'Polski 🇵🇱'),
    'voice3': ('it', 'Italiano 🇮🇹'),
    'voice4': ('fr', 'Français 🇫🇷'),
    'voice5': ('en', 'English 🇺🇲'),
    'voice6': ('es', 'Español 🇪🇸'),
    'voice7': ('de', 'Deutsch 🇩🇪'),
    'voice8': ('pt', 'Português 🇵🇹'),
}

# Функція для створення клавіатури першої сторінки
def get_first_page_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Українська 🇺🇦", callback_data='voice1'),
        InlineKeyboardButton("Polski 🇵🇱", callback_data='voice2'),
        InlineKeyboardButton("Italiano 🇮🇹", callback_data='voice3'),
        InlineKeyboardButton("Français 🇫🇷", callback_data='voice4')
    )
    markup.row(
        InlineKeyboardButton("⬅", callback_data='none'),
        InlineKeyboardButton("1/2", callback_data='none'),
        InlineKeyboardButton("➡", callback_data='x2')
    )
    return markup
# Функція для створення клавіатури другої сторінки
def get_second_page_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("English 🇺🇲", callback_data='voice5'),
        InlineKeyboardButton("Español 🇪🇸", callback_data='voice6'),
        InlineKeyboardButton("Deutsch 🇩🇪", callback_data='voice7'),
        InlineKeyboardButton("Português 🇵🇹", callback_data='voice8')
    )
    markup.row(
        InlineKeyboardButton("⬅", callback_data='x1'),
        InlineKeyboardButton("2/2", callback_data='none'),
        InlineKeyboardButton("➡", callback_data='none')
    )
    return markup

@dp.callback_query_handler(lambda call: call.data.startswith('voice') or call.data in ['x1', 'x2'], state="*")
async def callback_handler(call: types.CallbackQuery):
    try:
        user_id = call.from_user.id
        current_lang_code = user_voice.get(user_id, 'uk')  # Отримуємо поточний вибір

        # Якщо вибрали голос — перевіряємо, чи це не той самий голос
        if call.data.startswith('voice'):
            new_lang_code = voices[call.data][0]  # Отримуємо код мови
            if new_lang_code == current_lang_code:  # Якщо мова не змінилася
                await call.answer(f"❗Ви вже обрали {voices[call.data][1]}")
            else:
                user_voice[user_id] = new_lang_code

            # Оновлюємо клавіатуру
            markup = get_first_page_keyboard() if call.data in ['voice1', 'voice2', 'voice3', 'voice4'] else get_second_page_keyboard()
            await call.message.edit_text(
                f"📢 Обирайте <b>мову</b> та <b>голос</b> для зручного використання!\n<b>🔹Активна мова:</b> {voices[call.data][1]}\n\nВи можете змінити налаштування у будь-який момент ⚙️",
                parse_mode=types.ParseMode.HTML,
                reply_markup=markup
            )
            return

        # Якщо просто переходимо між сторінками, отримуємо останню вибрану мову
        lang_name = next((name for code, name in voices.values() if code == current_lang_code), "Українська 🇺🇦")

        # Визначаємо потрібну клавіатуру
        markup = get_second_page_keyboard() if call.data == 'x2' else get_first_page_keyboard()

        # Оновлюємо лише клавіатуру, без зміни тексту
        await call.message.edit_reply_markup(reply_markup=markup)

    except Exception as e:
        # Логування помилки для відслідковування
        pass

@dp.message_handler()
async def register_user(message: types.Message):
    add_user(message.from_user.id, message.from_user.first_name)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
