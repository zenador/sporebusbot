#!/usr/bin/env python

import json
import shelve
import re
from operator import itemgetter
from collections import defaultdict

import requests

LTA_ACCOUNT_KEY = 'YOUR LTA ACCOUNT KEY'

def saveAsJson(thing, filename):
	with open(filename+".json","w", encoding="utf-8") as thefile:
		json.dump(thing, thefile, sort_keys=True, indent=4, ensure_ascii=False)

def loadFromJson(filename):
	with open(filename+".json","r") as thefile:
		return json.load(thefile)

def saveDictAsShelve(dicty, filename):
	shelf = shelve.open(filename+'.shelve')
	#shelf.update(dicty) #not working with unicode keys
	for key in dicty:
		shelf[str(key)] = dicty[key]
	shelf.close()

def loadShelveAsDict(filename):
	shelf = shelve.open(filename+'.shelve')
	dicty = {}
	for key, val in shelf.items():
		dicty[key] = val
	return dicty

def downloadData(name):
	jsonDict = {}

	#Authentication parameters
	headers = {
		'AccountKey' : LTA_ACCOUNT_KEY,
		'accept' : 'application/json', #Request results in JSON
	}

	#API parameters
	target = 'http://datamall2.mytransport.sg/ltaodataservice/' + name #Resource URL

	skippy = 0
	results = 50

	while (results > 0):
		#Query parameters
		params = {"$skip": skippy}

		#Obtain results
		r = requests.get(target, params=params, headers=headers)

		#Parse JSON to print
		jsonObj = json.loads(r.content)
		#print json.dumps(jsonObj, sort_keys=True, indent=4)

		dictList = jsonObj["value"]

		for dicty in dictList:
			if name == "BusRoutes":
				key = "{}_{}_{}".format(dicty['BusStopCode'], dicty['ServiceNo'], dicty['Direction'])
			elif name == "BusStops":
				key = "{}".format(dicty['BusStopCode'])
			jsonDict[key] = dicty

		skippy += 50
		results = len(dictList)
		print(results, skippy)

	return jsonDict

def funnysort(listy):
	def safeInt(thing):
		try:
			return int(re.sub(r"(?<=\d)\D+$", "", thing))
		except ValueError:
			return 99999
	listy = [(i, safeInt(i)) for i in listy]
	return [a for a,b in sorted(listy, key=itemgetter(1, 0))]

def combineDicts(routes, stops):
	setDict = defaultdict(list)
	for key, val in routes.items():
		setDict[val["BusStopCode"]].append(val["ServiceNo"])
	for key, val in setDict.items():
		setDict[key] = funnysort(list(set(val)))
	for key, val in stops.items():
		val["Services"] = setDict[key]
	return stops

if __name__=="__main__":
	pass
	# routesetDict = downloadData("BusRoutes")
	# routesetDict = loadFromJson("routeset")
	# routesetDict = loadShelveAsDict("routeset")

	# saveAsJson(routesetDict, "routeset")
	# saveDictAsShelve(routesetDict, "routeset")

	# stopsetDict = downloadData("BusStops")
	# stopsetDict = loadFromJson("stopset")
	# stopsetDict = loadShelveAsDict("stopset")

	# saveAsJson(stopsetDict, "stopset")
	# saveDictAsShelve(stopsetDict, "stopset")

	# stopsetDictPlus = combineDicts(routesetDict, stopsetDict)
	# stopsetDictPlus = loadFromJson("stopsetplus")
	# stopsetDictPlus = loadShelveAsDict("stopsetplus")

	# saveAsJson(stopsetDictPlus, "stopsetplus")
	# saveDictAsShelve(stopsetDictPlus, "stopsetplus")
