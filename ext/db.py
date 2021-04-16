from datetime import datetime
from typing import Union, Optional

from pymongo import MongoClient
import discord
import yaml


def get(data, path: list):  # thanks to seojin200403
    if len(path) > 1:
        try:
            return get(data[path[0]], path[1:])
        except KeyError:
            return None
    else:
        try:
            return data[path[0]]
        except KeyError:
            return None


def config(query: Optional[str] = None) -> Union[str, int, dict, list]:
    with open('config.yml') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        if not query:
            return data
        else:
            return get(data, query.split('.'))


def emoji(query: str) -> str:
    emoji_id = config(f'emojis.{query}')
    return f"<:{query}:{emoji_id}>"


mongo = MongoClient(
    host=config('mongo.ip') if config('test') else 'localhost',
    port=27017,
    username=config('mongo.user'),
    password=config('mongo.password')
)

db = mongo['kkuttest' if config('test') else 'kkutbot']


def _collection_name(target) -> Optional[str]:
    if isinstance(target, discord.User) or isinstance(target, discord.Member) or isinstance(target, discord.ClientUser) or isinstance(target, int):
        return "user"
    elif isinstance(target, discord.Guild):
        return "guild"
    else:
        return None


def _get_id(target) -> int:
    return getattr(target, 'id', target)


def _get_name(target) -> str:
    return getattr(target, 'name', None)


def read(target, path: str = None):
    if target:
        collection = db[_collection_name(target)]
        main_data = collection.find_one({'_id': _get_id(target)})
        if not main_data:
            if _collection_name(target) == "user":
                main_data = config('default_data').copy()
            else:
                main_data = dict()
    else:
        main_data = db.general.find_one()

    if path is None:
        return main_data

    return get(main_data, path.split('.'))


def read_hanmaru(target, path: str = None):
    main_data = db.hanmaru.find_one({'_id': _get_id(target)})

    if path is None:
        return main_data

    return get(main_data, path.split('.'))


def write(target, path, value):
    collection = _collection_name(target)

    if collection == "user":
        if not read(target, 'register_date'):
            if data := db.unused.find_one({'_id': _get_id(target)}):
                db.user.insert_one(data)
                db.unused.remove({'_id': _get_id(target)})
            else:
                main_data = read(target)
                main_data['register_date'] = datetime.now()
                main_data['_id'] = _get_id(target)
                main_data['_name'] = _get_name(target)
                db.user.insert_one(main_data)
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
    data_before = read(target, path) or 0
    write(target, path, data_before + value)


def delete(target):
    db[_collection_name(target)].delete_one({'_id': _get_id(target)})
