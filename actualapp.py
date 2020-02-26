#!/usr/bin/env python

from flask import Flask#, send_from_directory

app = Flask(__name__)
app.config.from_pyfile('flaskapp.cfg')

@app.route('/')
def index():
	return '.'
'''
@app.route('/ATriggerVerify.txt')
def show_atrigger_verify():
	return send_from_directory("", 'ATriggerVerify.txt')
'''
