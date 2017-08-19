import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import Job
from telegram.ext import TypeHandler
from telegram.ext import Updater

from commands import CommandHolder
from deer import Deer
from config import *
from payment import YandexAgent
from utils import c_error, setup_logging

setup_logging('buybot.log', level=logging.INFO)

updater = Updater(telegram_token)
agent = YandexAgent(token=yandex_token)
deer = Deer(url=shop_url, email=shop_email, pay_agent=agent)
commands = CommandHolder(deer)


updater.dispatcher.add_handler(CommandHandler('start', commands.action_start))
updater.dispatcher.add_handler(CommandHandler('count', commands.action_count, pass_args=True))
updater.dispatcher.add_handler(CallbackQueryHandler(commands.inline_buy, pattern=r'^buy_([0-9]+)$', pass_groups=True))
updater.dispatcher.add_handler(CallbackQueryHandler(commands.inline_buy_confirm, pattern=r'^buy_(confirm|hide)_([0-9]+)$', pass_groups=True))
updater.dispatcher.add_handler(TypeHandler(Update, commands.action_unknown))
updater.job_queue.put(Job(commands._item_checker, 60, repeat=True), next_t=10.0)
updater.dispatcher.add_error_handler(c_error)

logging.info("Starting bot...")

updater.start_polling()
updater.idle()
