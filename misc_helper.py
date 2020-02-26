#!/usr/bin/env python

from datetime import datetime
from pytz import timezone
localTz = timezone('Singapore')
from dateutil import parser
from math import floor, sqrt, sin, cos, atan2, radians

def getNow():
	return datetime.now(localTz).replace(microsecond=0)

def getNowString():
	now = getNow()
	return now.strftime('%e %b %Y %a %I.%M %p').replace('  ', ' ')

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

def divideChunks(l, n):
	for i in range(0, len(l), n):
		yield l[i:i + n]
