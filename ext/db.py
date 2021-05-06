from copy import deepcopy
from datetime import datetime
from typing import Optional

import discord
from pymongo import MongoClient

from ext.config import config
from ext.config import get_nested_dict as get

mode = "test" if config("test") else "main"


def dbconfig(query: str):
    return config(f"mongo.{mode}.{query}")


db_options = {}
username = dbconfig('user')
password = dbconfig('password')

if all([username, password]):  # if both username and password is not None
    db_options['username'] = username
    db_options['password'] = password

mongo = MongoClient(
    host=dbconfig('ip'),
    port=dbconfig('port'),
    **db_options
)

db = mongo[dbconfig('db')]  # main database


def _collection_name(target) -> Optional[str]:
    """returns collection name"""
    if isinstance(target, (discord.User, discord.Member, discord.ClientUser, int)):
        return "user"
    elif isinstance(target, discord.Guild):
        return "guild"
    else:
        return None


def _get_id(target) -> int:
    """returns target id"""
    return getattr(target, 'id', target)


def _get_name(target) -> str:
    """returns target name"""
    return getattr(target, 'name', None)


def read(target, path: str = None):
    """returns value of target"""
    if target:
        collection = db[_collection_name(target)]
        main_data = collection.find_one({'_id': _get_id(target)})
        if not main_data:  # if target is not in db
            if _collection_name(target) == "user":
                main_data = deepcopy(config('default_data'))  # returns default user data schema
            else:
                main_data = {}  # returns empty dict
    else:
        main_data = db.general.find_one()

    if path is None:
        return main_data

    return get(main_data, path.split('.'))


def read_hanmaru(target, path: str = None):
    """returns value of target from hanmaru data"""
    main_data = db.hanmaru.find_one({'_id': _get_id(target)})

    if path is None:
        return main_data

    return get(main_data, path.split('.'))


def write(target, path, value):
    """writes value to db"""
    collection = _collection_name(target)

    if collection == "user":
        if not read(target, 'register_date'):  # if target is not in db
            if data := db.unused.find_one({'_id': _get_id(target)}):  # if target is in 'unused' collection
                db.user.insert_one(data)
                db.unused.remove({'_id': _get_id(target)})  # move data from 'unsued' collection to 'user' collection
            else:
                main_data = read(target)
                main_data['register_date'] = datetime.now()
                main_data['_id'] = _get_id(target)
                main_data['_name'] = _get_name(target)
                db.user.insert_one(main_data)  # create new data
        if (name := _get_name(target)) != read(target, '_name'):
            db.user.update_one({'id': _get_id(target)}, {'$set': {'_name': name}})
    if collection == "guild":
        if not read(target):
            db.guild.insert_one({'_id': _get_id(target)})

    if collection:
        db[collection].update_one({'_id': _get_id(target)}, {'$set': {path: value}})
    else:
        db.general.update_one({'_id': "general"}, {'$set': {path: value}})


def add(target, path: str, value: int):
    """adds value to target data"""
    data_before = read(target, path) or 0
    write(target, path, data_before + value)


def delete(target):
    """deletes the target data"""
    db[_collection_name(target)].delete_one({'_id': _get_id(target)})
