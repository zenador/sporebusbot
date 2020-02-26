#!/usr/bin/env python

import json
import redis

from actualapp import app

REDIS_URL = app.config['REDIS_URL']
REDIS_PORT = app.config['REDIS_PORT']
REDIS_PASSWORD = app.config['REDIS_PASSWORD']

db = redis.StrictRedis(host=REDIS_URL, port=REDIS_PORT, password=REDIS_PASSWORD, db=0)

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
