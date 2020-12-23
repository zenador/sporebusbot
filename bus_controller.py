#!/usr/bin/env python

from datetime import datetime, timedelta
from threading import Timer
from operator import itemgetter
import re
import json

import requests
from flask import request
import telegram
import hashlib, hmac

from actualapp import app
from bot_helper import sendLoc, sendMsg, updateMsg, makeInlineKeyboard, makeInlineKeyboardLayout
from db_helper import db, saveDbObj
from io_helper import readStopDict, readRouteDict, serialise
from misc_helper import getHaversineDistance, parseTime, getRemainingTime
from chat_controller import saveHistory, checkStar, makeStarButton, makeUnstarButton, makeServKey, getSavedService, makeNagKey, getSavedNag, makeRemindKey, getSavedRemind, makeTrackKey, getSavedTrack, addToQueue, removeFromQueue, hasExceededDailyLimit
from user_text import helpText

MAX_COUNT = 3 # does not include initial update, only follow-ups
MAX_TRACKING_COUNT = 8

LTA_ACCOUNT_KEY = app.config['LTA_ACCOUNT_KEY']
LTA_USER_ID = app.config['LTA_USER_ID']
POSTHOOK_API_KEY = app.config['POSTHOOK_API_KEY']
POSTHOOK_API_SIG = app.config['POSTHOOK_API_SIG']

def replyLocation(chat_id, loc):
	# not the fastest method, but the dataset is quite small so this is fast enough for now
	dicty = readStopDict()
	nearbyList = []
	for key, val in dicty.items():
		dist = getHaversineDistance(loc.latitude, loc.longitude, val["Latitude"], val["Longitude"])
		nearbyList.append((val, dist))
	nearbyList = sorted(nearbyList, key=itemgetter(1))[:5]
	nearbyListStr = ["_{}_ @ {} (*{}*), {:.2f} km\n{}".format(a["Description"], a["RoadName"], a["BusStopCode"], b, ", ".join(a["Services"])) for a,b in nearbyList]
	msg = "\n\n".join(nearbyListStr)
	makeData = lambda x: serialise({"c": "constr", "s": x})
	reply_markup = makeInlineKeyboard([(a["Description"], makeData(a["BusStopCode"])) for a,b in nearbyList], cols=2)
	sendMsg(chat_id, msg, reply_markup)

def replyBusInfo(chat_id, text, message=None):
	textAction = re.sub('\n.*', '', text)
	textList = [item.strip() for item in textAction.split(' ')]
	if len(textList) == 3:
		command, busStopNo, routeNo = textList
		processBusInfo(chat_id, busStopNo, routeNo, message=message)
	elif len(textList) == 2:
		command, busStopNo = textList
		processBusStop(chat_id, busStopNo)
	elif len(textList) == 1:
		# command = textList[0]
		success, busStopNo, routeNo = getSavedService(chat_id)
		if success:
			processBusInfo(chat_id, busStopNo, routeNo)
	else:
		sendMsg(chat_id, helpText)

def processBusInfo(chat_id, busStopNo, routeNo, message=None):
	dicty = readRouteDict()
	infoKey = str(busStopNo+'_'+routeNo+'_1')
	infoKey2 = str(busStopNo+'_'+routeNo+'_2')
	routeDict = None
	if infoKey in dicty:
		routeDict = dicty[infoKey]
	elif infoKey2 in dicty:
		routeDict = dicty[infoKey2]
	reply_markup = makeRoutesInlineKeyboard(busStopNo, chat_id)
	if routeDict:
		info = 'First and last bus timings for route '+routeNo+' at stop '+busStopNo
		info += '\nWeekdays: '+routeDict['WD_FirstBus']+' - '+routeDict['WD_LastBus']
		info += '\nSaturday: '+routeDict['SAT_FirstBus']+' - '+routeDict['SAT_LastBus']
		info += '\nSunday: '+routeDict['SUN_FirstBus']+' - '+routeDict['SUN_LastBus']
		updateMsg(chat_id, info, reply_markup=reply_markup, message=message)
		serviceKey = makeServKey(chat_id)
		saveDbObj(serviceKey, (busStopNo, routeNo))
	else:
		updateMsg(chat_id, 'No information found for route '+routeNo+' at stop '+busStopNo, reply_markup=reply_markup, message=message)

def processBusStop(chat_id, busStopNo, message=None):
	dicty = readStopDict()
	a = dicty.get(str(busStopNo))
	if a:
		text = "_{}_ @ {} (*{}*)\n{}".format(a["Description"], a["RoadName"], a["BusStopCode"], ", ".join(a["Services"]))
		reply_markup = makeRoutesInlineKeyboardInner(busStopNo, a, chat_id)
	else:
		text = "Could not find bus stop with code {}".format(busStopNo)
		reply_markup = None
	updateMsg(chat_id, text, reply_markup=reply_markup, message=message)

def sendBusStopLoc(message, busStopNo):
	dicty = readStopDict()
	a = dicty.get(str(busStopNo))
	if a:
		chat_id = message.chat.id
		sendLoc(chat_id, a["Latitude"], a["Longitude"])

def makeRoutesInlineKeyboardInner(busStopNo, a, chat_id):
	makeData = lambda x: serialise({"c": "constr", "s": busStopNo, "r": x})
	routeButtons = [(a, makeData(a)) for a in a["Services"]]
	stopButtons = [("Map", serialise({"c": "loc", "s": busStopNo}))]
	busStopName = a.get("Description", "")
	if len(checkStar(chat_id, busStopNo)) == 0:
		stopButtons.append(makeStarButton(busStopNo, busStopName))
	else:
		stopButtons.append(makeUnstarButton(busStopNo, busStopName))
	stopButtons.append(("Close", serialise({"c": "hide"})))
	layout = makeInlineKeyboardLayout(routeButtons, cols=6) + makeInlineKeyboardLayout(stopButtons, rows=1)
	return telegram.InlineKeyboardMarkup(inline_keyboard=layout)

def makeRoutesInlineKeyboard(busStopNo, chat_id):
	dicty = readStopDict()
	a = dicty.get(str(busStopNo))
	if a:
		return makeRoutesInlineKeyboardInner(busStopNo, a, chat_id)
	else:
		return None

def replyNextBus(chat_id, text, count, fromQ, message=None):
	if (fromQ):
		removeFromQueue(chat_id, text)
	textAction = re.sub('\n.*', '', text)
	textAction = re.sub('^/', '', textAction)
	textList = [item.strip() for item in textAction.split(' ')]
	interval = -1
	maxCount = 1
	isTracking = False
	isTrackingSilent = False
	textList[0] = textList[0].lower()
	if textList[0] == 'next':
		if len(textList) == 3:
			command, busStopNo, routeNo = textList
		elif len(textList) == 1:
			command = textList[0]
			success, busStopNo, routeNo = getSavedService(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo])
		else:
			updateMsg(chat_id, helpText, message=message)
			return
	elif textList[0] == 'remind':
		if len(textList) == 4:
			command, busStopNo, routeNo, interval = textList
			interval = float(interval)
		elif len(textList) == 3:
			command, busStopNo, routeNo = textList
			success, interval = getSavedRemind(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval)])
		elif len(textList) == 2:
			command, interval = textList
			interval = float(interval)
			success, busStopNo, routeNo = getSavedService(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval)])
		elif len(textList) == 1:
			command = textList[0]
			success, busStopNo, routeNo = getSavedService(chat_id)
			if success == False:
				return
			success, interval = getSavedRemind(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval)])
		else:
			updateMsg(chat_id, helpText, message=message)
			return
		remindKey = makeRemindKey(chat_id)
		db.set(remindKey, interval)
	elif textList[0] == 'nag':
		if len(textList) == 5:
			command, busStopNo, routeNo, interval, maxCount = textList
			interval = float(interval)
			maxCount = int(maxCount)
		elif len(textList) == 3:
			command, interval, maxCount = textList
			interval = float(interval)
			maxCount = int(maxCount)
			success, busStopNo, routeNo = getSavedService(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval), str(maxCount)])
		elif len(textList) == 1:
			command = textList[0]
			success, busStopNo, routeNo = getSavedService(chat_id)
			if success == False:
				return
			success, interval, maxCount = getSavedNag(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval), str(maxCount)])
		else:
			updateMsg(chat_id, helpText, message=message)
			return
		nagKey = makeNagKey(chat_id)
		saveDbObj(nagKey, (interval, maxCount))
	elif textList[0] == 'track' or textList[0] == 'tracks':
		if len(textList) == 4:
			command, busStopNo, routeNo, interval = textList
			interval = float(interval)
		elif len(textList) == 3:
			command, busStopNo, routeNo = textList
			success, interval = getSavedTrack(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval)])
		elif len(textList) == 2:
			command, interval = textList
			interval = float(interval)
			success, busStopNo, routeNo = getSavedService(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval)])
		elif len(textList) == 1:
			command = textList[0]
			success, busStopNo, routeNo = getSavedService(chat_id)
			if success == False:
				return
			success, interval = getSavedTrack(chat_id)
			if success == False:
				return
			text = ' '.join([command, busStopNo, routeNo, str(interval)])
		else:
			updateMsg(chat_id, helpText, message=message)
			return
		trackKey = makeTrackKey(chat_id)
		db.set(trackKey, interval)
		isTracking = True
		if (command == 'tracks'):
			isTrackingSilent = True
	else:
		sendMsg(chat_id, helpText)
		return

	if not fromQ:
		saveHistory(chat_id, text)

	if hasExceededDailyLimit(chat_id):
		return

	response = getNextBuses(busStopNo, routeNo)
	waitSecs = -1
	reply = ""
	if type(response) is tuple:
		responseStatus = response[0]
		reply = response[1]
		if responseStatus != -1:
			serviceKey = makeServKey(chat_id)
			saveDbObj(serviceKey, (busStopNo, routeNo))
		if responseStatus == 1:
			remTime = response[2]
			if interval != -1:
				if command == 'remind':
					if remTime <= 0:
						waitSecs = 0
					else:
						waitSecs = (remTime - interval)*60
				elif command == 'nag':
					waitSecs = (interval)*60
				elif command == 'track' or command == 'tracks':
					waitSecs = 0
					if remTime > interval:
						waitMins = 0
						trackSeq = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
						for (i, num) in enumerate(trackSeq):
							if remTime <= num:
								if i != 0:
									waitMins = trackSeq[i] - trackSeq[i-1]
								break
						if (remTime - waitMins) < interval:
							waitMins = remTime - interval
						waitSecs = (waitMins)*60

	shouldSendMsg = False
	if (not isTrackingSilent) or (waitSecs < 60) or (count > MAX_TRACKING_COUNT) or (count == 0):
		shouldSendMsg = True
	count += 1

	if maxCount > MAX_COUNT:
		maxCount = MAX_COUNT
		if (count == 1) and (waitSecs >= 60):
			shouldSendMsg = True
			reply += '\nDon\'t be insane, that\'s way too many times. Will only update you '+str(MAX_COUNT)+' more times'

	if isTracking:
		maxCount = MAX_TRACKING_COUNT
	
	if count == maxCount + 1:
		if shouldSendMsg and reply:
			reply = '_Final update_\n' + reply
	elif (count <= maxCount) and (waitSecs != -1):
		if waitSecs < 60:
			if shouldSendMsg and reply:
				reply = '_Final update_\n' + reply
		else:
			addToQueue(chat_id, text)
			callTimerHandler(waitSecs, chat_id, text, count)

	if shouldSendMsg and reply:
		reply_markup = makeRoutesInlineKeyboard(busStopNo, chat_id)
		updateMsg(chat_id, reply, reply_markup=reply_markup, message=message)

def callTimerThreading(waitSecs, chat_id, text, count):
	t = Timer(waitSecs, replyNextBus, [chat_id, text, count, True, None])
	t.start()

def callTimerApiPosthook(waitSecs, chat_id, text, count):
	url = 'https://api.posthook.io/v1/hooks'
	headers = {'Content-Type': 'application/json', 'X-API-Key': POSTHOOK_API_KEY}
	postAt = (datetime.utcnow() + timedelta(seconds=waitSecs)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
	payload = {'path': "timer_posthook", "postAt": postAt, "data": {"chat_id": chat_id, "text": text, "count": count}}
	r = requests.post(url, headers=headers, data=json.dumps(payload))
	res = r.json()
	if res.get("error"):
		callTimerDown(waitSecs, chat_id, text, count)

def callTimerDown(waitSecs, chat_id, text, count):
	sendMsg(chat_id, "Sorry, timer service is not available now, so we can only reply with info on demand but can't send alerts.")
	removeFromQueue(chat_id, text)

callTimerHandler = callTimerApiPosthook

shouldCheckQueueUponStart = callTimerHandler == callTimerThreading

@app.route('/timer_posthook', methods=['POST'])
def handleTimerApiPosthook():
	signature = request.headers.get('X-Ph-Signature')
	signature_computed = hmac.new(
		key=POSTHOOK_API_SIG.encode('utf-8'),
		msg=request.data,
		digestmod=hashlib.sha256
	).hexdigest()
	if not hmac.compare_digest(signature, signature_computed):
		return 'unauthorised'
	return handleTimerApi(request.json.get("data", {}))

def handleTimerApi(data):
	chat_id = data.get("chat_id")
	text = data.get("text")
	count = data.get("count")
	replyNextBus(chat_id, text, count, True, None)
	return 'ok'

def formatTiming(timey, load, visit):
	remTime = getRemainingTime(timey)
	if remTime == 0:
		remTime = 'Arr'
	elif remTime == -1:
		remTime = ''
	else:
		remTime = str(remTime)
	if visit == '2':
		remTime = '('+remTime+')'
	presuffix = ''
	if load == 'SEA': #Seats Available
		presuffix = '*'
	elif load == 'SDA': #Standing Available
		presuffix = ''
	elif load == 'LSD': #Limited Standing
		presuffix = '_'
	return presuffix + remTime + presuffix

def getNextBuses(busStopNo, routeNo):
	url = 'http://datamall2.mytransport.sg/ltaodataservice/BusArrivalv2'
	headers = {'accept': 'application/json', 'AccountKey': LTA_ACCOUNT_KEY}
	payload = {'BusStopCode': busStopNo, 'ServiceNo': routeNo}
	r = requests.get(url, params=payload, headers=headers)
	rjson = r.json()

	dicty = readStopDict()
	busStopName = dicty.get(str(busStopNo), {}).get("Description", "")

	services = rjson.get('Services', [])
	if len(services) > 0:
		service = services[0]

		busList = ['NextBus', 'NextBus2', 'NextBus3']
		timingList = []
		for bus in busList:
			if bus in service:
				timey = parseTime(service[bus]['EstimatedArrival'])
				if timey is None:
					continue
				load = service[bus]['Load']
				visit = service[bus]['VisitNumber']
				timingList.append((timey, load, visit))

		successText = 'Arriving in: {arr_times}\n(Next buses for route {routeNo} at stop {busStopNo})\n_{busStopName}_'.format(
			arr_times=' '.join([formatTiming(timey, load, visit) for (timey, load, visit) in timingList]),
			routeNo=routeNo,
			busStopNo=busStopNo,
			busStopName=busStopName,
		)

		return (1, successText, getRemainingTime(timingList[0][0]))
	else:
		failureText = 'No currently operating services found for route {} at stop {}\n_{}_'.format(routeNo, busStopNo, busStopName)
		return (-1, failureText)
