from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, TypeHandler

from flight_tracker.bot.access import guard, on_access_decision, start
from flight_tracker.config import Settings
from flight_tracker.db import connect, migrate
from flight_tracker.repositories.user_repository import UserRepository
from flight_tracker.services.access_service import AccessService


def build_application(settings: Settings) -> Application:
    conn = connect(settings.database_path)
    migrate(conn)

    access = AccessService(UserRepository(conn), settings.owner_chat_id)
    access.ensure_owner()

    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.bot_data.update(
        settings=settings,
        owner_chat_id=settings.owner_chat_id,
        access=access,
    )

    app.add_handler(TypeHandler(Update, guard), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_access_decision, pattern=r"^access:"))
    return app
