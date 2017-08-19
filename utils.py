import logging
from functools import wraps
from telegram import Update

from config import permitted_users


def decorate_all_functions(function_decorator):
	def decorator(cls):
		for name, obj in vars(cls).items():
			if callable(obj):
				try:
					obj = obj.__func__  # unwrap Python 2 unbound method
				except AttributeError:
					pass  # not needed in Python 3
				setattr(cls, name, function_decorator(obj))
		return cls

	return decorator


def pre_filter(bot, update, func_name):
	# check_db()
	d = update.to_dict()
	if 'callback_query' in d:
		user = update.callback_query.from_user
		cmd_type = 'I'
		data = update.callback_query.data
	else:
		if 'message' not in d:
			logging.info("Unknown update: {}".format(d))
			cmd_type = 'U'
			data = None
		else:
			user = update.message.from_user
			cmd_type = 'T'
			data = update.message.text[:150].replace("\n", " / ")
			if update.message.text[:1] == '/':
				cmd_type = 'C'

	user_chat_id = ''
	# logging.info("such c_id{} u_id{}".format(chat_id(update), user_id(update)))
	if user_id(update) != chat_id(update):
		user_chat_id = '.{}'.format(chat_id(update))
	logging.info("{fn}/{id}{chat} {type}_{name} {payload}".format(
		fn=user.first_name,
		id=user_id(update),
		chat=user_chat_id,
		type=cmd_type,
		name=func_name,
		payload=data
	))


def has_access(bot, update):
	trust_users = permitted_users

	if type(update) is not Update:
		logging.warning("Passed invalid object: {}".format(update))
		return False

	if 'callback_query' in update.to_dict():
		trust = update.callback_query.from_user.id in trust_users
	elif 'message' in update.to_dict():
		trust = update.message.from_user.id in trust_users
	else:
		return False
	if not trust:
		logging.warning("Unauthorized command execution: {}".format(update))
		bot.sendMessage(chat_id=update.message.chat.id, text="Sorry, please go away 🤔")

	return trust


def access_checker(func):
	@wraps(func)
	def wrapper(*args, **kw):
		# logging.info('{} called'.format(func.__name__))
		skip = func.__name__[:1] == '_'
		if not skip and not has_access(bot=args[1], update=args[2]):
			logging.warning("{} denied".format(func.__name__))
			return None
		try:
			if not skip:
				pre_filter(bot=args[1], update=args[2], func_name=func.__name__)
			res = func(*args, **kw)
		finally:
			# print('{} finished'.format(func.__name__))
			pass
		return res

	return wrapper


def extract_ids(update):
	if 'callback_query' in update.to_dict():
		user_id = update.callback_query.from_user.id
		chat_id = update.callback_query.message.chat.id
		message_id = update.callback_query.message.message_id
		inline_id = update.callback_query.id
	else:
		user_id = update.message.from_user.id
		chat_id = update.message.chat.id
		message_id = update.message.message_id
		inline_id = None

	return dict(userId=user_id, chatId=chat_id, messageId=message_id, inlineId=inline_id)


def user_id(update):
	return extract_ids(update)['userId']


def chat_id(update):
	return extract_ids(update)['chatId']


def message_id(update):
	return extract_ids(update)['messageId']


def inline_id(update):
	return extract_ids(update)['inlineId']


def c_error(bot, update, error):
	logging.warning('Update "%s" caused error "%s"' % (update, error))


def setup_logging(file, level=logging.INFO):
	logging.basicConfig(level=level, filename=file, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	console = logging.StreamHandler()
	console.setLevel(level)
	formatter = logging.Formatter('[%(asctime)s] %(name)s: %(levelname)s %(message)s')
	console.setFormatter(formatter)
	logging.getLogger().addHandler(console)

	watcher = logging.FileHandler('watcher.log')
	watcher.setLevel(level)
	watcher.setFormatter(formatter)
	logging.getLogger('watcher').addHandler(watcher)
