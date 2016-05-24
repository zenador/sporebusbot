#!/usr/bin/env python

from flask import Flask
import redis

app = Flask(__name__)
app.config.from_pyfile('flaskapp.cfg')

REDISCLOUD_URL = app.config['REDISCLOUD_URL']
REDISCLOUD_PORT = app.config['REDISCLOUD_PORT']
REDISCLOUD_PASSWORD = app.config['REDISCLOUD_PASSWORD']

KEY_DAILY_LOG = '_dailylog'

db = redis.StrictRedis(host=REDISCLOUD_URL, port=REDISCLOUD_PORT, password=REDISCLOUD_PASSWORD, db=0)
for key in db.scan_iter("*"+KEY_DAILY_LOG):
    db.delete(key)
