#!/usr/bin/env python

from math import ceil
import logging
import traceback

import telegram

from actualapp import app
from misc_helper import divideChunks

TOKEN = app.config['BOT_TOKEN']
APP_URL = app.config['APP_URL']

global bot
bot = telegram.Bot(token=TOKEN)

@app.route('/'+TOKEN+'/set_webhook', methods=['GET', 'POST'])
def setWebhook():
	s = bot.setWebhook(APP_URL+'/'+TOKEN+'/HOOK')
	if s:
		return "webhook setup ok"
	else:
		return "webhook setup failed"

def sendLoc(chat_id, lat, lon):
	try:
		bot.send_location(chat_id=chat_id, latitude=lat, longitude=lon)
	except Exception:
		logging.exception("Couldn't send location to {}".format(chat_id))

def sendMsg(chat_id, text, reply_markup=None):
	try:
		try:
			bot.send_message(chat_id=chat_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)
		except telegram.error.TelegramError:
			traceback.print_exc()
			bot.send_message(chat_id=chat_id, text="Reply is in invalid format")
	except Exception:
		logging.exception("Couldn't send message to {}".format(chat_id))

def editMsg(msg, text, reply_markup=None):
	bot.editMessageText(chat_id=msg.chat.id, message_id=msg.message_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)

def editMsgReplyMarkup(msg, reply_markup=None):
	bot.editMessageReplyMarkup(chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=reply_markup)

def updateMsg(chat_id, text, reply_markup=None, message=None):
	if message:
		editMsg(message, text, reply_markup=reply_markup)
	else:
		sendMsg(chat_id, text, reply_markup=reply_markup)

def makeInlineKeyboardLayout(arr, rows=None, cols=None):
	buttons = [telegram.InlineKeyboardButton(text=text, callback_data=data) for text,data in arr]
	if rows:
		cols = int(ceil(len(buttons) / rows))
	elif not cols:
		cols = 1
	return list(divideChunks(buttons, cols))

def makeInlineKeyboard(arr, rows=None, cols=None):
	layout = makeInlineKeyboardLayout(arr, rows, cols)
	return telegram.InlineKeyboardMarkup(inline_keyboard=layout)

def replaceButtonInMarkup(reply_markup, button_info, row=-1, col=-1):
	inline_keyboard = reply_markup.inline_keyboard
	text, callback_data = button_info
	def modify_item(i, item, length):
		target_pos = (length + col) if col < 0 else col
		if i == target_pos:
			return telegram.InlineKeyboardButton(text=text, callback_data=callback_data)
		return item
	def modify_row(i, this_row, length):
		target_pos = (length + row) if row < 0 else row
		if i == target_pos:
			return [modify_item(i, item, len(this_row)) for i, item in enumerate(this_row)]
		return this_row
	inline_keyboard = [modify_row(i, this_row, len(inline_keyboard)) for i, this_row in enumerate(inline_keyboard)]
	return telegram.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
