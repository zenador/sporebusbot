#!/usr/bin/env python

import json

def loadFromJson(filename):
	with open(filename+".json","r") as thefile:
		return json.load(thefile)

def readStopDict():
	return loadFromJson('stopsetplus')

def readRouteDict():
	return loadFromJson('routeset')

def serialise(x):
	s = json.dumps(x, separators=(',', ':'))
	length = len(s.encode('utf-8'))
	if length > 64:
		raise ValueError('Serialised string is too long. Telegram limits to max 64 bytes but this is {} bytes. {}'.format(length, s))
	return s

def deserialise(x):
	return json.loads(x)
