#!/usr/bin/env python

from datetime import datetime, timedelta
import re

import telegram

from bot_helper import sendMsg, editMsgReplyMarkup, replaceButtonInMarkup
from db_helper import db, initDbList, getDbObj, trimDbList, addToDbList, popFromDbList
from io_helper import serialise
from misc_helper import getNowString
from user_text import helpText

KEY_FAV = '_fav'
KEY_HIST = '_hist'
KEY_STAR = '_star'
KEY_SERVICE = '_service'
KEY_NAG = '_nag'
KEY_REMIND = '_remind'
KEY_TRACK = '_track'
KEY_DAILY_LOG = '_dailylog'
KEY_QUEUE = '_queue'
MAX_DAILY_LOG = 100

def makeFavKey(chat_id):
	return str(chat_id) + KEY_FAV

def makeHistKey(chat_id):
	return str(chat_id) + KEY_HIST

def makeStarKey(chat_id):
	return str(chat_id) + KEY_STAR

def makeServKey(chat_id):
	return str(chat_id) + KEY_SERVICE

def makeNagKey(chat_id):
	return str(chat_id) + KEY_NAG

def makeRemindKey(chat_id):
	return str(chat_id) + KEY_REMIND

def makeTrackKey(chat_id):
	return str(chat_id) + KEY_TRACK

def makeDailyLogKey(chat_id):
	return str(chat_id) + KEY_DAILY_LOG

def makeQueueKey(chat_id):
	return str(chat_id) + KEY_QUEUE

def editFav(chat_id, text):
	textList = [item.strip() for item in text.split('|')]
	if (len(textList) == 2):
		command, action = textList
		command = command.lower()
		command = re.sub('^/', '', command)
	else:
		sendMsg(chat_id, helpText)
		return
	favKey = makeFavKey(chat_id)
	initDbList(favKey)
	matchingIndexes = [i for (i, val) in enumerate(getDbObj(favKey)) if val==action]

	if command == 'save':
		if len(matchingIndexes) == 0:
			addToDbList(favKey, action)
			reply_markup = telegram.ReplyKeyboardRemove()
			sendMsg(chat_id, "Command saved to your favourites!", reply_markup=reply_markup)
		else:
			sendMsg(chat_id, 'You have already saved this command')
	elif command == 'delete':
		if len(matchingIndexes) == 0:
			sendMsg(chat_id, 'No matching commands found in your favourites')
		else:
			for i in matchingIndexes:
				popFromDbList(favKey, i)
			reply_markup = telegram.ReplyKeyboardRemove()
			sendMsg(chat_id, "Command removed from your favourites!", reply_markup=reply_markup)
	else:
		sendMsg(chat_id, helpText)

def showFav(chat_id):
	favKey = makeFavKey(chat_id)
	initDbList(favKey)
	currFavs = getDbObj(favKey)
	if len(currFavs) == 0:
		reply_markup = telegram.ReplyKeyboardRemove()
		sendMsg(chat_id, "You have no favourite commands", reply_markup=reply_markup)
	else:
		reply_markup = telegram.ReplyKeyboardMarkup(keyboard=[[item] for item in currFavs], resize_keyboard=True, one_time_keyboard=True)
		sendMsg(chat_id, "Here are your favourite commands:", reply_markup=reply_markup)

def saveHistory(chat_id, text):
	textAction = re.sub('\n.*', '', text)
	histKey = makeHistKey(chat_id)
	initDbList(histKey)
	matchingIndexes = [i for (i, val) in enumerate(getDbObj(histKey)) if re.sub('\n.*', '', val)==textAction]
	for i in matchingIndexes:
		popFromDbList(histKey, i)
	addToDbList(histKey, textAction+'\n'+getNowString())
	trimDbList(histKey, 5)

def showHist(chat_id):
	histKey = makeHistKey(chat_id)
	initDbList(histKey)
	history = getDbObj(histKey)
	if len(history) == 0:
		reply_markup = telegram.ReplyKeyboardRemove()
		sendMsg(chat_id, "You have no recent commands", reply_markup=reply_markup)
	else:
		reply_markup = telegram.ReplyKeyboardMarkup(keyboard=[[item] for item in history], resize_keyboard=True, one_time_keyboard=True)
		sendMsg(chat_id, "Here are your recent commands:", reply_markup=reply_markup)

def checkStar(chat_id, busStopNo):
	starKey = makeStarKey(chat_id)
	initDbList(starKey)
	matchingIndexes = [i for (i, val) in enumerate(getDbObj(starKey)) if val.split("\n")[0]==busStopNo]
	return matchingIndexes

def makeStarButton(busStopNo, busStopName):
	return ("Star", serialise({"c": "star", "s": busStopNo, "n": busStopName[:30]}))

def makeUnstarButton(busStopNo, busStopName):
	return ("Unstar", serialise({"c": "unstar", "s": busStopNo, "n": busStopName[:30]}))

def editStar(message, busStopNo, command, busStopName):
	chat_id = message.chat.id
	matchingIndexes = checkStar(chat_id, busStopNo)
	starKey = makeStarKey(chat_id)
	if command == 'star':
		if len(matchingIndexes) == 0:
			addToDbList(starKey, busStopNo+'\n'+busStopName)
		newButton = makeUnstarButton(busStopNo, busStopName)
	elif command == 'unstar':
		for i in matchingIndexes:
			popFromDbList(starKey, i)
		newButton = makeStarButton(busStopNo, busStopName)
	reply_markup = replaceButtonInMarkup(message.reply_markup, newButton, col=-2)
	editMsgReplyMarkup(message, reply_markup=reply_markup)

def showStar(chat_id):
	starKey = makeStarKey(chat_id)
	initDbList(starKey)
	currStars = getDbObj(starKey)
	if len(currStars) == 0:
		reply_markup = telegram.ReplyKeyboardRemove()
		sendMsg(chat_id, "You have no starred bus stops", reply_markup=reply_markup)
	else:
		reply_markup = telegram.ReplyKeyboardMarkup(keyboard=[["/info {}".format(item)] for item in currStars], resize_keyboard=True, one_time_keyboard=True)
		sendMsg(chat_id, "Here are your starred bus stops:", reply_markup=reply_markup)

def getSavedService(chat_id):
	key = makeServKey(chat_id)
	keyInfo = getDbObj(key)
	if keyInfo is not None:
		busStopNo, routeNo = keyInfo
		success = True
	else:
		sendMsg(chat_id, 'Can\'t retrieve last successfully queried bus stop and route number')
		busStopNo, routeNo = '', ''
		success = False
	return success, busStopNo, routeNo

def getSavedNag(chat_id):
	key = makeNagKey(chat_id)
	keyInfo = getDbObj(key)
	if keyInfo is not None:
		interval, maxCount = keyInfo
		success = True
	else:
		sendMsg(chat_id, 'Can\'t retrieve last nag interval and repeats')
		interval, maxCount = -1, 1
		success = False
	return success, interval, maxCount

def getSavedRemind(chat_id):
	key = makeRemindKey(chat_id)
	keyInfo = db.get(key)
	if keyInfo is not None:
		interval = float(keyInfo)
		success = True
	else:
		sendMsg(chat_id, 'Can\'t retrieve last remind interval')
		interval = -1
		success = False
	return success, interval

def getSavedTrack(chat_id):
	key = makeTrackKey(chat_id)
	keyInfo = db.get(key)
	if keyInfo is not None:
		interval = float(keyInfo)
		success = True
	else:
		sendMsg(chat_id, 'Can\'t retrieve last track interval')
		interval = -1
		success = False
	return success, interval

def getDailyLog(chat_id):
	dailyLogKey = makeDailyLogKey(chat_id)
	dailyLog = db.get(dailyLogKey)
	if dailyLog is None:
		dailyLog = 0
	return int(dailyLog)

def replyDailyLog(chat_id):
	dailyLog = getDailyLog(chat_id)
	sendMsg(chat_id, 'Today you have made '+str(dailyLog)+' next bus queries')

def hasExceededDailyLimit(chat_id):
	dailyLog = getDailyLog(chat_id)
	if (dailyLog >= MAX_DAILY_LOG):
		sendMsg(chat_id, 'You have reached your daily limit for next bus queries')
		return True
	dailyLogKey = makeDailyLogKey(chat_id)
	db.incr(dailyLogKey, 1)
	db.expireat(dailyLogKey, getDailyLimitExpiryDate())
	return False

def getDailyLimitExpiryDate():
	now = datetime.utcnow()
	then = datetime(now.year, now.month, now.day, 19) # 3am sgt
	if then <= now:
		then += timedelta(days=1)
	return then

def addToQueue(chat_id, req):
	qKey = makeQueueKey(chat_id)
	initDbList(qKey)
	addToDbList(qKey, req)

def removeFromQueue(chat_id, req):
	qKey = makeQueueKey(chat_id)
	initDbList(qKey)
	matchingIndexes = [i for (i, val) in enumerate(getDbObj(qKey)) if val==req]
	if len(matchingIndexes) > 0:
		popFromDbList(qKey, matchingIndexes[0])

def checkQueueUponStart():
	for key in db.scan_iter("*"+KEY_QUEUE):
		key = key.decode("utf-8")
		currQ = getDbObj(key)
		if len(currQ) > 0:
			chat_id = key.replace(KEY_QUEUE, "")
			sendMsg(chat_id, 'The server restarted while you had pending requests. You will not receive updates for your pending requests below, so please resend them:\n'+'\n'.join(['- `{}`'.format(item) for item in currQ]))
		db.delete(key)
