# TaleBrush 
# Copyright (c) 2022-present NAVER Corp.
# GPLv3

'''server/app.py - main api app declaration'''
from flask import Flask, jsonify, send_from_directory, g, request
from flask_cors import CORS
import sqlite3
import os
import json
import datetime
import requests
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE=os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, '../database.db'))
SCHEMA=os.path.join(BASE_DIR, '../config.sql')

'''Main wrapper for app creation'''
app = Flask(__name__, static_folder='../build')
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
ML_URL = os.environ.get('ML_URL', 'http://localhost:5001/')

print("Server running!")

def init_db():
    '''Create the event log table from config.sql if it does not exist yet'''
    os.makedirs(os.path.dirname(os.path.abspath(DATABASE)), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='DataDump';").fetchone()
    if not exists:
        with open(SCHEMA) as f:
            conn.executescript(f.read())
    conn.close()

init_db()

def get_db():
    if 'sqlite_db' not in g:
        g.sqlite_db = sqlite3.connect(DATABASE)
    return g.sqlite_db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('sqlite_db', None)
    if db is not None:
        db.close()

##
# API routes
##

@app.route('/api/items')
def items():
  '''Sample API route for data'''
  print('items')
  return jsonify([{'title': 'A'}, {'title': 'B'}])

@app.route('/api/storeEvent', methods=['GET', 'POST'])
def storeEvent():
  '''storing...'''
  if request.method == 'POST':
    # print(request.get_data())
    d = json.loads(request.get_data())
    print(d)
    conn = get_db()
    cursor = get_db().cursor()
    print(get_db())
    # cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    # tables = cursor.fetchall()
    # print(tables)
    c_state = json.dumps(d['c_state'])
    action = d['action']
    user = d['user']
    t = datetime.datetime.now()
    # cursor.execute('INSERT INTO DataDump (User, Data, Action) values (?,?,?);', (user, c_state, action))
    cursor.execute('INSERT INTO DataDump (User, Data, Datetime, Action) values (?,?,?,?);', (user, c_state, t, action))
    conn.commit()
    return jsonify({'result': 'success'})
  return jsonify({'result': 'nothing'})

@app.route('/api/labelSentence', methods=['GET', 'POST'])
def labelSentence():
  '''Sample API route for data'''
  if request.method == 'POST':
    print('data', request.data)
    ret = requests.post(ML_URL+'labelSentence', json= json.loads(request.data))
    # print('ret', ret.json(), 'ret')
    # print(ret.json())
    return jsonify(ret.json())
  return jsonify({'result': 'nothing'})

@app.route('/api/continuingGeneration', methods=['GET', 'POST'])
def continuingGeneration():
  '''Sample API route for data'''
  if request.method == 'POST':
    print(request.data)
    ret = requests.post(ML_URL+'continuingGeneration', json=json.loads(request.data))
    # print('ret', ret.json(), 'ret')
    
    return jsonify(ret.json())
  return jsonify({'result': 'nothing'})

@app.route('/api/infillingGeneration', methods=['GET', 'POST'])
def infillingGeneration():
  '''Sample API route for data'''
  if request.method == 'POST':
    print(request.data)
    ret = requests.post(ML_URL+'infillingGeneration', json=json.loads(request.data))
    print('ret', ret, 'ret')
    return jsonify(ret.json())
  return jsonify({'result': 'nothing'})
  

##
# View route
##

# @app.route('/', defaults={'path': ''})
@app.route('/talebrush')
def index():
  '''Return index.html for all non-api routes'''
  #pylint: disable=unused-argument
  # print(path)
  # if path != "" and os.path.exists(app.static_folder + '/' + path):
  #   print('oh?')
  #   return send_from_directory(app.static_folder, path)
  # print(app.static_folder)
  print(app.static_folder)
  return send_from_directory(app.static_folder, 'index.html')

