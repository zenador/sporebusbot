#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.abspath('.'), 'lib'))

import re

from flask import request
import telegram

from actualapp import app
from bot_helper import bot, TOKEN, sendMsg, editMsg, editMsgReplyMarkup, makeInlineKeyboard
from io_helper import serialise, deserialise
from user_text import helpText, helpTextFull
from bus_controller import replyLocation, sendBusStopLoc, replyNextBus, replyBusInfo, processBusStop, shouldCheckQueueUponStart
from chat_controller import editStar, editFav, replyDailyLog, showFav, showHist, showStar, checkQueueUponStart

@app.route('/'+TOKEN+'/HOOK', methods=['POST'])
def webhookHandler():
	if request.method == "POST":
		# retrieve the message in JSON and then transform it to Telegram object
		update = telegram.Update.de_json(request.get_json(force=True), bot)
		message = update.message
		callback = update.callback_query
		if message:
			chat_id = message.chat.id
			text = message.text
			loc = message.location
			if loc:
				replyLocation(chat_id, loc)
			elif text: # may be None if it's a sticker or something
				replyCommand(chat_id, text)
		elif callback:
			message = callback.message
			data = deserialise(callback.data)
			command = data.get("c")
			if command == "constr":
				callbackConstr(message, data)
			elif command in ["star", "unstar"]:
				editStar(message, data.get("s"), command)
			elif command == "loc":
				sendBusStopLoc(message, data.get("s"))
			elif command == "hide":
				editMsgReplyMarkup(message, reply_markup=None)
				# editMsgReplyMarkup(message, reply_markup=makeInlineKeyboard([]))
			bot.answerCallbackQuery(callback.id)
	return 'ok'

def replyCommand(chat_id, text, message=None):
	text = text.strip()
	lowerText = text.lower()
	lowerText = re.sub('^/', '', lowerText)
	if re.match(r'next *', lowerText) or re.match(r'remind *', lowerText) or re.match(r'nag *', lowerText) or re.match(r'tracks? *', lowerText):
		replyNextBus(chat_id, text, 0, False, message)
	elif re.match(r'info *', lowerText):
		replyBusInfo(chat_id, text, message)
	elif re.match(r'save *\|', lowerText) or re.match(r'delete *\|', lowerText):
		editFav(chat_id, text)
	elif re.match(r'counter *', lowerText):
		replyDailyLog(chat_id)
	elif re.match(r'fav *', lowerText):
		showFav(chat_id)
	elif re.match(r'history *', lowerText):
		showHist(chat_id)
	elif re.match(r'starred *', lowerText):
		showStar(chat_id)
	elif re.match(r'help *', lowerText):
		sendMsg(chat_id, helpTextFull)
	else:
		sendMsg(chat_id, helpText)

def callbackConstr(message, data):
	chat_id = message.chat.id
	busStopNo = data.get("s")
	routeNo = data.get("r")
	action = data.get("a")
	if action:
		if action in ["next", "info"]:
			text = "/{} {} {}".format(action, busStopNo, routeNo)
			replyCommand(chat_id, text, message)
		elif action in ["remind", "track", "tracks"]:
			interval = data.get("x")
			if interval:
				text = "/{} {} {} {}".format(action, busStopNo, routeNo, interval)
				replyCommand(chat_id, text, message)
			else:
				makeData = lambda x: serialise(dict(data, **{"x": x}))
				intervals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30]
				reply_markup = makeInlineKeyboard([(a, makeData(a)) for a in intervals], rows=3)
				if action == "track":
					template = "How many minutes before the next bus {} arrives at stop {} would you like your last alert?"
				else:
					template = "How many minutes before the next bus {} arrives at stop {} would you like your alert?"
				editMsg(message, template.format(routeNo, busStopNo), reply_markup=reply_markup)
	elif routeNo:
		makeData = lambda x: serialise(dict(data, **{"a": x}))
		actions = ["next", "remind", "track", "tracks", "info"]
		reply_markup = makeInlineKeyboard([(a, makeData(a)) for a in actions], rows=1)
		editMsg(message, "Choose an action (as described in /help) for stop {} and route {}:".format(busStopNo, routeNo), reply_markup=reply_markup)
	else:
		processBusStop(chat_id, busStopNo, message)

if (shouldCheckQueueUponStart):
	checkQueueUponStart()
