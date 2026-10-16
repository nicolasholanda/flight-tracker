import warnings

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, TypeHandler
from telegram.warnings import PTBUserWarning

from flight_tracker.bot.access import guard, on_access_decision, start
from flight_tracker.bot.admin import on_revoke, revoke_command, users_command
from flight_tracker.bot.search import search_conversation
from flight_tracker.config import Settings
from flight_tracker.db import connect, migrate
from flight_tracker.providers.google_flights import GoogleFlightsProvider
from flight_tracker.repositories.search_request_repository import SearchRequestRepository
from flight_tracker.repositories.user_repository import UserRepository
from flight_tracker.services.access_service import AccessService
from flight_tracker.services.city_resolver import CityResolver
from flight_tracker.services.quota_service import QuotaService
from flight_tracker.services.search_service import SearchService

warnings.filterwarnings("ignore", message=r".*per_message.*", category=PTBUserWarning)


def build_application(settings: Settings) -> Application:
    conn = connect(settings.database_path)
    migrate(conn)

    access = AccessService(UserRepository(conn), settings.owner_chat_id)
    access.ensure_owner()
    provider = GoogleFlightsProvider(settings.currency, settings.language)

    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.bot_data.update(
        settings=settings,
        owner_chat_id=settings.owner_chat_id,
        access=access,
        city_resolver=CityResolver.from_csv(),
        search=SearchService(provider, settings.request_delay_seconds),
        quota=QuotaService(SearchRequestRepository(conn), settings.max_searches_per_user_per_hour),
    )

    app.add_handler(TypeHandler(Update, guard), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_access_decision, pattern=r"^access:"))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("revoke", revoke_command))
    app.add_handler(CallbackQueryHandler(on_revoke, pattern=r"^admin:revoke:"))
    app.add_handler(search_conversation())
    return app
