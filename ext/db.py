from copy import deepcopy
from datetime import datetime
from typing import Optional

import discord
from motor.motor_asyncio import AsyncIOMotorClient

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

client = AsyncIOMotorClient(
    host=dbconfig('ip'),
    port=dbconfig('port'),
    **db_options
)

db = client[dbconfig('db')]  # main database


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


async def read(target, path: str = None):
    """returns value of target"""
    if target:
        collection = db[_collection_name(target)]
        main_data = await collection.find_one({'_id': _get_id(target)})
        if not main_data:  # if target is not in db
            if _collection_name(target) == "user":
                main_data = deepcopy(config('default_data'))  # returns default user data schema
            else:
                main_data = {}  # returns empty dict
    else:
        main_data = await db.general.find_one()

    if path is None:
        return main_data

    return get(main_data, path.split('.'))


async def read_hanmaru(target, path: str = None):
    """returns value of target from hanmaru data"""
    main_data = await db.hanmaru.find_one({'_id': _get_id(target)})

    if path is None:
        return main_data

    return get(main_data, path.split('.'))


async def write(target, path, value):
    """writes value to db"""
    collection = _collection_name(target)

    if collection == "user":
        if not (await read(target, 'register_date')):  # if target is not in db
            if data := await db.unused.find_one({'_id': _get_id(target)}):  # if target is in 'unused' collection
                await db.user.insert_one(data)
                await db.unused.remove({'_id': _get_id(target)})  # move data from 'unsued' collection to 'user' collection
            else:
                main_data = await read(target)
                main_data['register_date'] = datetime.now()
                main_data['_id'] = _get_id(target)
                main_data['_name'] = _get_name(target)
                await db.user.insert_one(main_data)  # create new data
        if (name := _get_name(target)) != (await read(target, '_name')):
            await db.user.update_one({'id': _get_id(target)}, {'$set': {'_name': name}})
    elif (collection == "guild") and (not await read(target)):
        await db.guild.insert_one({'_id': _get_id(target)})

    if collection:
        await db[collection].update_one({'_id': _get_id(target)}, {'$set': {path: value}})
    else:
        await db.general.update_one({'_id': "general"}, {'$set': {path: value}})


async def add(target, path: str, value: int):
    """adds value to target data"""
    data_before = (await read(target, path)) or 0
    await write(target, path, data_before + value)


async def delete(target):
    """deletes the target data"""
    await db[_collection_name(target)].delete_one({'_id': _get_id(target)})


async def append(target, path: str, value):
    """appends value to target data(list)"""
    await db[_collection_name(target)].update_one(
        {'_id': _get_id(target)},
        {
            '$push': {
                path: value
            }
        }
    )
