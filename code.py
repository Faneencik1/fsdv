import os
import logging
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("messages.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PORT = int(os.environ.get('PORT', 5000))  # Для Render
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # Для webhook

# ID кастомных эмодзи из вашего эмодзи-пака (замените на свои)
CUSTOM_EMOJIS = {
    "success": "5208880351690112495",      # ID кастомного эмодзи для успеха
    "error": "5352703271536454445",        # ID для ошибки
    "welcome": "5341463333532882949",      # ID для приветствия
    "warning": "5447644880824181073",      # ID для предупреждения
}

async def is_admin(update: Update) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return update.effective_user.id == ADMIN_ID

async def send_with_custom_emoji(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, emoji_id: str = None) -> None:
    """
    Отправляет сообщение с кастомным эмодзи
    Кастомные эмодзи работают только для Premium пользователей
    """
    try:
        if emoji_id:
            # Для inline кастомных эмодзи используем MessageEntity
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                entities=[{
                    "type": "custom_emoji",
                    "offset": 0,  # позиция в тексте где начинается эмодзи
                    "length": 1,   # длина эмодзи (обычно 1)
                    "custom_emoji_id": emoji_id
                }]
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"Ошибка при отправке кастомного эмодзи: {e}")
        # Отправляем без кастомного эмодзи в случае ошибки
        await context.bot.send_message(chat_id=chat_id, text=text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Пользователь @{user.username} (ID: {user.id}) запустил бота.")
    await update.message.reply_text(
        "{get_custom_emoji_text('welcome')} Привет! Напиши своё сообщение сюда, и оно опубликуется в канале (имя канала).\n"
        "Бот был сделан: @faneencikmusic"
    )

async def forward_media_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    caption = f"Медиа от @{user.username} (ID: {user.id})"
    
    try:
        # Сначала отправляем информацию об отправителе
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Медиафайлы от @{user.username} (ID: {user.id}):"
        )

        if update.message.media_group_id:
            if not context.user_data.get('processing_media_group'):
                context.user_data['processing_media_group'] = True
                context.user_data['media_group'] = []
                context.user_data['caption'] = update.message.caption or caption
            
            if update.message.photo:
                media = InputMediaPhoto(media=update.message.photo[-1].file_id)
            elif update.message.video:
                media = InputMediaVideo(media=update.message.video.file_id)
            
            if update.message.caption:
                context.user_data['caption'] = update.message.caption
            
            context.user_data['media_group'].append(media)
            return
            
        # Обработка одиночных медиафайлов
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=update.message.caption
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=ADMIN_ID,
                video=update.message.video.file_id,
                caption=update.message.caption
            )
        elif update.message.voice:
            await context.bot.send_voice(
                chat_id=ADMIN_ID,
                voice=update.message.voice.file_id,
                caption=update.message.caption
            )
            logger.info(f"Голосовое сообщение от @{user.username}")
            await update.message.reply_text("{get_custom_emoji_text('success')} Ваше голосовое сообщение переслано!")
            return

        # Обработка медиагрупп (альбомов)
        if 'processing_media_group' in context.user_data:
            if len(context.user_data['media_group']) > 0:
                # Отправляем медиагруппу отдельным сообщением
                await context.bot.send_media_group(
                    chat_id=ADMIN_ID,
                    media=context.user_data['media_group']
                )
                logger.info(f"Альбом из {len(context.user_data['media_group'])} файлов от @{user.username}")
            
            context.user_data.pop('processing_media_group', None)
            context.user_data.pop('media_group', None)
            context.user_data.pop('caption', None)
            
        await update.message.reply_text("{get_custom_emoji_text('success')} Медиа пересланы!")
        logger.info(f"Медиа от @{user.username} (ID: {user.id})")

    except Exception as e:
        logger.error(f"Ошибка пересылки медиа: {e}")
        await update.message.reply_text("{get_custom_emoji_text('warning')} Произошла ошибка при пересылке медиа")

async def forward_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text

    logger.info(f"@{user.username} (ID: {user.id}): {text}")

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Сообщение от @{user.username} (ID: {user.id}):"
        )
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=text
        )
        await update.message.reply_text("{get_custom_emoji_text('success')} Ваше сообщение было переслано!")
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

async def get_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update):
        await update.message.reply_text("{get_custom_emoji_text('error')} У вас нет прав для выполнения этой команды.")
        return

    try:
        with open("messages.log", "rb") as log_file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=log_file,
                caption="📄 Лог-файл бота"
            )
        logger.info(f"Администратор @{update.effective_user.username} запросил лог-файл")
    except FileNotFoundError:
        await update.message.reply_text("{get_custom_emoji_text('warning')} Лог-файл не найден")
    except Exception as e:
        logger.error(f"Ошибка отправки лога: {e}")
        await update.message.reply_text("{get_custom_emoji_text('warning')} Произошла ошибка при отправке лога")

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getlog", get_log))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.VOICE, forward_media_group))

    # Определяем режим работы
    if WEBHOOK_URL and os.environ.get('RENDER'):
        logger.info("🚀 Запуск в режиме webhook (Render)")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        logger.info("🔄 Запуск в режиме polling (локально)")
        app.run_polling(
            poll_interval=1.0,
            timeout=10,
            allowed_updates=Update.ALL_TYPES
        )

if __name__ == "__main__":
    main()
