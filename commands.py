import random
import re

import logging
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup

from perekrestok import Perekrestok
from utils import chat_id, decorate_all_functions, access_checker, message_id


@decorate_all_functions(access_checker)
class CommandHolder:
	def __init__(self, deer):
		self.deer = deer
		self.count = 1
		self.unknown_choices = {
			'Открыть магазин': self.action_choose,
			# 'Узнать количество': self.action_count,
		}
		self.prev_items = dict()

	def action_start(self, bot, update):
		keyboard = []
		for choice, handler in self.unknown_choices.items():
			keyboard.append([KeyboardButton(choice)])

		return bot.sendMessage(chat_id=chat_id(update), text="Привет! Давай откроем магазин", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

	def action_count(self, bot, update, args):
		# noinspection PyBroadException
		try:
			count = int(args[0])
		except:
			return bot.sendMessage(chat_id=chat_id(update), text="Введено неверное количество: {}".format(args))

		self.count = count
		return bot.sendMessage(chat_id=chat_id(update), text="Количество изменено на {}".format(self.count))

	def action_choose(self, bot, update):
		keyboard = []
		goods = []
		for item in self.deer.list_items():
			keyboard.append(InlineKeyboardButton(item['title'], callback_data='buy_{}'.format(item['id'])))
			goods.append(item['title'])
		bot.sendMessage(chat_id=chat_id(update), text="Доступны товары:\n\n  {}".format('\n  '.join(goods)), reply_markup=InlineKeyboardMarkup([[k] for k in keyboard]))

	def inline_buy(self, bot, update, groups):
		id = groups[0]

		keyboard = [
			InlineKeyboardButton(text='Купить', callback_data='buy_confirm_{}'.format(id)),
			InlineKeyboardButton(text='Отменить', callback_data='buy_hide_{}'.format(id)),
		]
		if id not in self.deer.items:
			return bot.sendMessage(chat_id=chat_id(update), text="Невозможно купить товар\n  /start")

		item = self.deer.items[id]
		total_cost = self.count * float(item['cost']) * 1.005
		text = "Купить этот товар? \n  название: {title}\n  цена: {cost}₽\n  кол-во: {count}\n  мин. кол-во: {mincount}\n\n  Общая цена: {total:.2f} руб".format(
			title=item['title'],
			cost=item['cost'],
			count=self.count,
			mincount=item['mincount'],
			total=total_cost
		)

		bot.sendMessage(chat_id=chat_id(update), text=text, reply_markup=InlineKeyboardMarkup([keyboard]))

	def inline_buy_confirm(self, bot, update, groups):
		method, id = groups[0], groups[1]
		bot.editMessageReplyMarkup(chat_id=chat_id(update), message_id=message_id(update), reply_markup=InlineKeyboardMarkup([]))

		if method != 'confirm':
			return bot.sendMessage(chat_id=chat_id(update), text="Покупка отменена")

		bot.sendMessage(chat_id=chat_id(update), text="Подождите, покупаем товар...")
		content = self.deer.buy(id, self.count)
		if 'error' in content:
			return bot.sendMessage(chat_id=chat_id(update), text="Ошибка: {}".format(content['error']))

		items = content['content'].strip()
		for item_part in items.split("\n"):
			match = re.search('([^:]+):([0-9]+).*Balance:[^\d]*([0-9]+)', item_part.strip())
			if match:
				login, password = match.group(1), match.group(2)
				bot.sendMessage(chat_id=chat_id(update), text=login)
				bot.sendMessage(chat_id=chat_id(update), text="Старый пароль: {}".format(password))
				bot.sendMessage(chat_id=chat_id(update), text="Баланс: {}".format(match.group(3)))

				perekrestok = Perekrestok(login, password)
				auth = perekrestok.auth()
				if not auth['ok']:
					bot.sendMessage(chat_id=chat_id(update), text="Ошибка перекрестка: {}".format(auth['error']))
				else:
					bot.sendMessage(chat_id=chat_id(update), text="Реальный баланс: {} руб".format(auth['balance']))
					new_password = '{}{}'.format(str(random.randint(0, 9)) * 3, str(random.randint(0, 9)) * 3)
					changed = perekrestok.change_password(new_password)
					if changed:
						bot.sendMessage(chat_id=chat_id(update), text="Пароль изменен. Новый пароль: {}".format(new_password))
						bot.sendMessage(chat_id=chat_id(update), text=new_password)
					else:
						bot.sendMessage(chat_id=chat_id(update), text="Пароль не удалось изменить на {}".format(new_password))

		return bot.sendMessage(chat_id=chat_id(update), text="Товар куплен: \n{}".format(content['content']))

	def _item_checker(self, bot, job):
		# logging.info("Checking items")
		self.deer.list_items()
		for id, item in self.deer.items.items():
			logging.getLogger('watcher').info("Item / {count}\tpcs: {item} ({id}; {cost}$)".format(id=id, item=item['title'], count=item['count'], cost=item['cost']))

	def action_unknown(self, bot, update):
		text = update.message.text
		if text in self.unknown_choices:
			handler = self.unknown_choices[text]
			return handler(bot, update)

		bot.sendMessage(chat_id=chat_id(update), text="Неизвестная команда\n  /start")
