#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.abspath('.'), 'lib'))

from datetime import datetime, timedelta
from pytz import timezone
from dateutil import parser
localTz = timezone('Singapore')
from threading import Timer
from math import floor, sqrt, sin, cos, atan2, radians
from operator import itemgetter
import re
import json
import redis
import shelve
import logging

import telegram
from flask import Flask, request
import requests

app = Flask(__name__)
app.config.from_pyfile('flaskapp.cfg')

TOKEN = app.config['BOT_TOKEN']
APP_URL = app.config['APP_URL']
LTA_ACCOUNT_KEY = app.config['LTA_ACCOUNT_KEY']
LTA_USER_ID = app.config['LTA_USER_ID']

REDIS_URL = app.config['REDIS_URL']
REDIS_PORT = app.config['REDIS_PORT']
REDIS_PASSWORD = app.config['REDIS_PASSWORD']

global bot
bot = telegram.Bot(token=TOKEN)

db = redis.StrictRedis(host=REDIS_URL, port=REDIS_PORT, password=REDIS_PASSWORD, db=0)

KEY_FAV = '_fav'
KEY_HIST = '_hist'
KEY_SERVICE = '_service'
KEY_NAG = '_nag'
KEY_REMIND = '_remind'
KEY_TRACK = '_track'
KEY_DAILY_LOG = '_dailylog'
KEY_QUEUE = '_queue'
MAX_COUNT = 3 # does not include initial update, only follow-ups
MAX_TRACKING_COUNT = 8
MAX_DAILY_LOG = 100

@app.route('/'+TOKEN+'/HOOK', methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        # retrieve the message in JSON and then transform it to Telegram object
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        chat_id = update.message.chat.id
        text = update.message.text.encode('utf-8')
        loc = update.message.location
        
        if loc:
            replyLocation(chat_id, loc)
        else:
            replyCommand(chat_id, text)

    return 'ok'

def replyCommand(chat_id, text):
    text = text.strip()
    lowerText = text.lower()
    lowerText = re.sub('^/', '', lowerText)
    if re.match(r'next *', lowerText) or re.match(r'remind *', lowerText) or re.match(r'nag *', lowerText) or re.match(r'tracks? *', lowerText):
        replyNextBus(chat_id, text, 0, False)
    elif re.match(r'info *', lowerText):
        replyBusInfo(chat_id, text)
    elif re.match(r'save *\|', lowerText) or re.match(r'delete *\|', lowerText):
        editFav(chat_id, text)
    elif re.match(r'counter *', lowerText):
        replyDailyLog(chat_id)
    elif re.match(r'fav *', lowerText):
        showFav(chat_id)
    elif re.match(r'history *', lowerText):
        showHist(chat_id)
    elif re.match(r'help *', lowerText):
        sendMsg(chat_id, helpTextFull)
    else:
        sendMsg(chat_id, helpText)

helpText = 'Please enter /help to read about the available commands'

helpTextFull = '''
Send your location to see the 5 nearest bus stops.

/next - Shows the ETAs for the next few buses
*/next [Bus Stop #] [Bus Route #]*
_/next 17179 184_

/remind - Shows the ETAs for the next few buses and sends another alert X minutes before the next bus according to the first ETA
*/remind [Bus Stop #] [Bus Route #] [X Integer]*
_/remind 17179 184 2_

/track - Shows the ETAs for the next few buses and sends more alerts at decreasing intervals until the next bus is X minutes from arriving
*/track [Bus Stop #] [Bus Route #] [X Integer]*
_/track 17179 184 2_

As an alternative, replace 'track' with 'tracks' to not receive the alerts in the middle, and only get an alert about X minutes before the bus arrives. This works similar to remind, but may be more accurate as it keeps checking in between (sends more queries), though less reliable as it is less tested.

/nag - Shows the ETAs for the next few buses and sends more alerts at X minute intervals for a maximum of Y times
*/nag [Bus Stop #] [Bus Route #] [X Integer] [Y Integer]*
_/nag 17179 184 2 1_

/info - Shows the first and last bus timings for that route at that bus stop, or info about the stop if route is omitted
*/info [Bus Stop #] [Bus Route #]*
_/info 17179 184_
*/info [Bus Stop #]*
_/info 17179_

For all commands, you may omit the bus stop number and route number to use your last successfully queried numbers instead, e.g.
/next

*/remind [X Integer]*
_/remind 2_

*/track [X Integer]*
_/track 2_

*/nag [X Integer] [Y Integer]*
_/nag 2 1_

You may also omit the extra parameters to use your last used settings for that particular command, e.g.
*/remind [Bus Stop #] [Bus Route #]*
_/remind 17179 184_

*/track [Bus Stop #] [Bus Route #]*
_/track 17179 184_

Or you could omit both.
/remind
/track
/nag
/info

/fav - Shows a list of shortcuts to the favourite commands that you have saved

/history - Shows your recent commands

/save - Saves a new command to your favourites
*_/save|[command]
[Description of command]*
_/save|remind 17179 184 2
Clementi bus stop_

/delete - Removes an existing command from your favourites
*/delete|[command]
[Description of command]*
_/delete|remind 17179 184 2
Clementi bus stop_

Commands can be entered with or without the starting slash.

Legend for bus timings:
*Seats Available*
Standing Available
_Limited Standing_
(Second Visit)
'''

def initDbList(key):
    thingy = db.get(key)
    if thingy is None:
        db.set(key, json.dumps([]))
        return True
    return False

def getDbObj(key):
    thingy = db.get(key)
    if thingy is None:
        return None
    obj = json.loads(thingy)
    return obj

def saveDbObj(key, obj):
    thingy = json.dumps(obj)
    db.set(key, thingy)

def trimDbList(key, length):
    thingy = db.get(key)
    listy = json.loads(thingy)
    listy = listy[-length:]
    thingy = json.dumps(listy)
    db.set(key, thingy)

def addToDbList(key, newItem):
    thingy = db.get(key)
    listy = json.loads(thingy)
    listy.append(newItem)
    thingy = json.dumps(listy)
    db.set(key, thingy)

def popFromDbList(key, popIndex):
    thingy = db.get(key)
    listy = json.loads(thingy)
    listy.pop(popIndex)
    thingy = json.dumps(listy)
    db.set(key, thingy)

def addToQueue(chat_id, req):
    qKey = str(chat_id) + KEY_QUEUE
    initDbList(qKey)
    addToDbList(qKey, req)

def removeFromQueue(chat_id, req):
    qKey = str(chat_id) + KEY_QUEUE
    initDbList(qKey)
    matchingIndexes = [i for (i, val) in enumerate(getDbObj(qKey)) if val==req]
    if len(matchingIndexes) > 0:
        popFromDbList(qKey, matchingIndexes[0])

def editFav(chat_id, text):
    textList = [item.strip() for item in text.split('|')]
    if (len(textList) == 2):
        command, action = textList
        command = command.lower()
        command = re.sub('^/', '', command)
    else:
        sendMsg(chat_id, helpText)
        return
    favKey = str(chat_id) + KEY_FAV
    initDbList(favKey)
    matchingIndexes = [i for (i, val) in enumerate(getDbObj(favKey)) if val==action]

    if command == 'save':
        if len(matchingIndexes) == 0:
            addToDbList(favKey, action)
            reply_markup = telegram.ReplyKeyboardHide()
            sendMsg(chat_id, "Command saved to your favourites!", reply_markup=reply_markup)
        else:
            sendMsg(chat_id, 'You have already saved this command')
    elif command == 'delete':
        if len(matchingIndexes) == 0:
            sendMsg(chat_id, 'No matching commands found in your favourites')
        else:
            for i in matchingIndexes:
                popFromDbList(favKey, i)
            reply_markup = telegram.ReplyKeyboardHide()
            sendMsg(chat_id, "Command removed from your favourites!", reply_markup=reply_markup)
    else:
        sendMsg(chat_id, helpText)

def showFav(chat_id):
    favKey = str(chat_id) + KEY_FAV
    initDbList(favKey)
    currFavs = getDbObj(favKey)
    if len(currFavs) == 0:
        sendMsg(chat_id, "You have no favourite commands")
    else:
        reply_markup = telegram.ReplyKeyboardMarkup(keyboard=[[item] for item in currFavs], resize_keyboard=True, one_time_keyboard=True)
        sendMsg(chat_id, "Here are your favourite commands:", reply_markup=reply_markup)

def saveHistory(chat_id, text):
    textAction = re.sub('\n.*', '', text)
    histKey = str(chat_id) + KEY_HIST
    initDbList(histKey)
    matchingIndexes = [i for (i, val) in enumerate(getDbObj(histKey)) if re.sub('\n.*', '', val)==textAction]
    for i in matchingIndexes:
        popFromDbList(histKey, i)
    addToDbList(histKey, textAction+'\n'+getNowString())
    trimDbList(histKey, 5)

def showHist(chat_id):
    histKey = str(chat_id) + KEY_HIST
    initDbList(histKey)
    history = getDbObj(histKey)
    if len(history) == 0:
        sendMsg(chat_id, "You have no recent commands")
    else:
        reply_markup = telegram.ReplyKeyboardMarkup(keyboard=[[item] for item in history], resize_keyboard=True, one_time_keyboard=True)
        sendMsg(chat_id, "Here are your recent commands:", reply_markup=reply_markup)

def replyBusInfo(chat_id, text):
    textAction = re.sub('\n.*', '', text)
    textList = [item.strip() for item in textAction.split(' ')]
    if len(textList) == 3:
        command, busStopNo, routeNo = textList
        processBusInfo(chat_id, busStopNo, routeNo)
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

def processBusStop(chat_id, busStopNo):
    shelf = shelve.open('stopsetplus.shelve')
    a = shelf.get(busStopNo)
    if a:
        msg = "_{}_ @ {} (*{}*)\n{}".format(a["Description"], a["RoadName"], a["BusStopCode"], ", ".join(a["Services"]))
        sendLoc(chat_id, a["Latitude"], a["Longitude"])
    else:
        msg = "Could not find bus stop with code {}".format(busStopNo)
    sendMsg(chat_id, msg)

def processBusInfo(chat_id, busStopNo, routeNo):
    shelf = shelve.open('routeset.shelve')
    infoKey = str(busStopNo+'_'+routeNo+'_1') #shelf can't handle unicode
    infoKey2 = str(busStopNo+'_'+routeNo+'_2')
    routeDict = None
    if infoKey in shelf:
        routeDict = shelf[infoKey]
    elif infoKey2 in shelf:
        routeDict = shelf[infoKey2]
    if routeDict:
        info = 'First and last bus timings for route '+routeNo+' at stop '+busStopNo
        info += '\nWeekdays: '+routeDict['WD_FirstBus']+' - '+routeDict['WD_LastBus']
        info += '\nSaturday: '+routeDict['SAT_FirstBus']+' - '+routeDict['SAT_LastBus']
        info += '\nSunday: '+routeDict['SUN_FirstBus']+' - '+routeDict['SUN_LastBus']
        sendMsg(chat_id, info)
        serviceKey = str(chat_id) + KEY_SERVICE
        saveDbObj(serviceKey, (busStopNo, routeNo))
    else:
        sendMsg(chat_id, 'No information found for route '+routeNo+' at stop '+busStopNo)

def getSavedService(chat_id):
    key = str(chat_id) + KEY_SERVICE
    keyInfo = getDbObj(key)
    if keyInfo is not None:
        busStopNo, routeNo = keyInfo
        success = True
    else:
        sendMsg(chat_id, 'Can\'t retrieve last successfully queried bus stop and route number')
        busStopNo, routeNo = '', ''
        success = False
    return success, busStopNo, routeNo

def getSavedRemind(chat_id):
    key = str(chat_id) + KEY_REMIND
    keyInfo = db.get(key)
    if keyInfo is not None:
        interval = float(keyInfo)
        success = True
    else:
        sendMsg(chat_id, 'Can\'t retrieve last remind interval')
        interval = -1
        success = False
    return success, interval

def getSavedNag(chat_id):
    key = str(chat_id) + KEY_NAG
    keyInfo = getDbObj(key)
    if keyInfo is not None:
        interval, maxCount = keyInfo
        success = True
    else:
        sendMsg(chat_id, 'Can\'t retrieve last nag interval and repeats')
        interval, maxCount = -1, 1
        success = False
    return success, interval, maxCount

def getSavedTrack(chat_id):
    key = str(chat_id) + KEY_TRACK
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
    dailyLogKey = str(chat_id) + KEY_DAILY_LOG
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
    dailyLogKey = str(chat_id) + KEY_DAILY_LOG
    db.incr(dailyLogKey, 1)
    db.expireat(dailyLogKey, getDailyLimitExpiryDate())
    return False

def getDailyLimitExpiryDate():
    now = datetime.utcnow()
    then = datetime(now.year, now.month, now.day, 19) # 3am sgt
    if then <= now:
        then += timedelta(days=1)
    return then

def replyNextBus(chat_id, text, count, fromQ):
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
            sendMsg(chat_id, helpText)
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
            sendMsg(chat_id, helpText)
            return
        remindKey = str(chat_id) + KEY_REMIND
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
            sendMsg(chat_id, helpText)
            return
        nagKey = str(chat_id) + KEY_NAG
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
            sendMsg(chat_id, helpText)
            return
        trackKey = str(chat_id) + KEY_TRACK
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
            serviceKey = str(chat_id) + KEY_SERVICE
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
            t = Timer(waitSecs, replyNextBus, [chat_id, text, count, True])
            t.start()
            addToQueue(chat_id, text)

    if shouldSendMsg and reply:
        sendMsg(chat_id, reply)
        
def sendMsg(chat_id, text, reply_markup=None):
    try:
        try:
            bot.send_message(chat_id=chat_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)
        except telegram.error.TelegramError:
            bot.send_message(chat_id=chat_id, text="Reply is in invalid format")
    except Exception:
        logging.exception("Couldn't send message to {}".format(chat_id))
        
def sendLoc(chat_id, lat, lon):
    try:
        bot.send_location(chat_id=chat_id, latitude=lat, longitude=lon)
    except Exception:
        logging.exception("Couldn't send location to {}".format(chat_id))
  
@app.route('/'+TOKEN+'/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook(APP_URL+'/'+TOKEN+'/HOOK')
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"

@app.route('/')
def index():
    return '.'

def getNow():
    return datetime.now(localTz).replace(microsecond=0)

def getNowString():
    now = getNow()
    return now.strftime('%e %b %Y %a %l.%M %p').replace('  ', ' ')

def parseTime(timeStr):
    if timeStr == '' or timeStr == None:
        return None
    #time1 = datetime.strptime(timeStr[:19], '%Y-%m-%dT%H:%M:%S')
    timey = parser.parse(timeStr[:19])
    timey = localTz.localize(timey)
    return timey

def getRemainingTime(timey):
    if timey == None:
        return -1
    diffDelta = timey-getNow()
    diffMins = floor(diffDelta.total_seconds()/60)
    if diffMins < 0:
        diffMins = 0
    return int(diffMins)

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

        successText = 'Arriving in: '+' '.join([formatTiming(timey, load, visit) for (timey, load, visit) in timingList])+'\n(Next buses for route '+routeNo+' at stop '+busStopNo+')'

        return (1, successText, getRemainingTime(timingList[0][0]))
    else:
        return (-1, 'No currently operating services found for route '+routeNo+' at stop '+busStopNo)
'''
def getSquaredDistance(lat1, long1, lat2, long2):
    return (lat1 - lat2)**2 + (long1 - long2)**2
'''
def getHaversineDistance(lat1, long1, lat2, long2):
    R = 6373.0 # approximate radius of earth in km

    lat1 = radians(lat1)
    long1 = radians(long1)
    lat2 = radians(lat2)
    long2 = radians(long2)

    dlon = long2 - long1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

def replyLocation(chat_id, loc):
    # not the fastest method, but the dataset is quite small so this is fast enough for now
    shelf = shelve.open('stopsetplus.shelve')
    nearbyList = []
    for key, val in shelf.iteritems():
        dist = getHaversineDistance(loc.latitude, loc.longitude, val["Latitude"], val["Longitude"])
        nearbyList.append((val, dist))
    nearbyList = sorted(nearbyList, key=itemgetter(1))[:5]
    nearbyList = ["_{}_ @ {} (*{}*), {:.2f} km\n{}".format(a["Description"], a["RoadName"], a["BusStopCode"], b, ", ".join(a["Services"])) for a,b in nearbyList]
    msg = "\n\n".join(nearbyList)
    sendMsg(chat_id, msg)

def checkQueueUponStart():
    for key in db.scan_iter("*"+KEY_QUEUE):
        currQ = getDbObj(key)
        if len(currQ) > 0:
            chat_id = key.replace(KEY_QUEUE, "")
            sendMsg(chat_id, 'The server restarted while you had pending requests. You will not receive updates for your pending requests below, so please resend them:\n'+'\n'.join(['- '+item for item in currQ]))
        db.delete(key)

checkQueueUponStart()
