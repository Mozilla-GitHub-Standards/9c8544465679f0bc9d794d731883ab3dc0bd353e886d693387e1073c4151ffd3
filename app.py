#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
sys.dont_write_bytecode = True

from ruamel import yaml
from subprocess import check_output
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo

app = Flask(__name__)

SCRIPT_PATH = os.path.dirname(__file__)
DBNAME = 'mozsmdb'

app.config['MONGO_DBNAME'] = DBNAME
app.config['MONGO_URI'] = 'mongodb://localhost:27017/' + DBNAME

mongo = PyMongo(app)

class MissingJsonError(Exception):
    pass

def serialize(change):
    change.pop('_id', None)
    return change

def response(changes):
    return jsonify(dict(changes=[serialize(change) for change in changes]))

def stderr(*items):
    print(' '.join([repr(item) for item in items]), file=sys.stderr)

def unique_id():
    return str(mongo.db.seqs.find_and_modify(
        query={ 'collection' : 'changes' },
        update={'$inc': {'id': 1}},
        fields={'id': 1, '_id': 0},
        new=True
    ).get('id'))

@app.before_first_request
def setup_db():
    mongo.db.seqs.insert({'collection': 'changes', 'id': 0})

@app.route('/')
def about():
    return 'MozSM REST api\n'

@app.route('/change', methods=['GET'], defaults={'id': None})
@app.route('/change/<id>', methods=['GET'])
def query(id=None):
    stderr('id =', id)
    if id is None:
        changes = list(mongo.db.changes.find())
    else:
        changes = [mongo.db.changes.find_one_or_404({'id': id})]
    return response(changes)

@app.route('/change/create', methods=['POST'])
def create():
    json = request.json
    if json is None:
        raise MissingJsonError

    json['id'] = unique_id()
    _id = mongo.db.changes.insert(json)
    change = mongo.db.changes.find_one(dict(_id=_id))
    return response([change])

@app.route('/nuke', methods=['DELETE'])
def nuke():
    mongo.db.seqs.remove({})
    mongo.db.changes.remove({})
    setup_db()
    return 'all data nuked! nice one ;)\n'

if __name__ == '__main__':
    app.run(debug=True)
