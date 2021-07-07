import logging
import asyncio
from datetime import datetime
from typing import Optional, Union, Any
from copy import deepcopy

import discord
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

try:
    import uvloop
except ImportError:
    uvloop = None

from .config import config, get_nested_dict


logger = logging.getLogger('kkutbot')
MODE = "test" if config('test') else "main"


def dbconfig(query: str):
    """
    gets about db configuration value in 'config.yml' file
    Parameters
    ----------
    query : str
    Returns
    -------
    Any
        value about db configuration in 'config.yml' file
    """
    return config(f'mongo.{MODE}.{query}')


db_options = {}

if all([
    username := dbconfig('user'),
    password := dbconfig('password')
]):
    db_options['username'] = username
    db_options['password'] = password

if uvloop:
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
else:
    loop = asyncio.get_event_loop()

client = AsyncIOMotorClient(
    host=dbconfig('ip'),
    port=dbconfig('port'),
    io_loop=loop,
    **db_options
)

logger.info("mongoDB에 연결됨")


db = client[dbconfig('db')]


def get_collection(target) -> AsyncIOMotorCollection:
    """
    returns proper collection of the target

    Arguments
    ---------
    target
        targeted object to get collection

    Returns
    -------
    AsyncIOMotorCollection
        proper collection of the target
    """
    if isinstance(target, (discord.User, discord.Member, discord.ClientUser, int)):
        return db.user
    elif isinstance(target, discord.Guild):
        return db.guild
    elif target is None:
        return db.general


def _get_id(target) -> Union[int, str]:
    """
    returns target id

    Arguments
    ---------
    target
        targeted object to get id

    Returns
    -------
    Union[int, str]
        target id
    """
    if target is None:
        return "general"
    return getattr(target, 'id', target)


def _get_name(target) -> str:
    """
    returns target name

    Arguments
    ---------
    target
        targeted object to get name

    Returns
    -------
    Union[int, str]
        target name
    """
    return getattr(target, 'name', None)


async def read(target, path: Optional[str] = None) -> Any:
    """
    reads target info

    Arguments
    ---------
    target
        targeted object to read info
    path: Optional[str]
        data path in nested dictionary

    Returns
    -------
    Any
        target's info
    """
    if target:
        collection = get_collection(target)
        main_data = await collection.find_one({'_id': _get_id(target)})
        if not main_data:
            if collection.name == "user":
                main_data = deepcopy(config("default_data.user"))
            elif collection.name == "guild":
                main_data = deepcopy(config("default_data.guild"))
    else:
        main_data = deepcopy(config("default_data.general"))

    if path is None:
        return main_data

    return get_nested_dict(main_data, path.split('.'))


async def write(target, path: str, value):
    """
    writes value to target

    Arguments
    ---------
    target
        targeted object to write value
    path: Optional[str]
        data path in nested dictionary
    value
        value to write into DB
    """
    collection = get_collection(target)

    if collection.name == "user":
        if not (await read(target, 'registered')):
            if data := await db.unused.find_one({'_id': _get_id(target)}):
                await db.user.insert_one(data)
                await db.unused.delete_one({'_id': _get_id(target)})
            else:
                main_data = await read(target)
                main_data['register_date'] = datetime.now()
                main_data['_id'] = _get_id(target)
                main_data['name'] = _get_name(target)
                await db.user.insert_one(main_data)
        if (name := _get_name(target)) != (await read(target, 'name')):
            await db.user.update_one({'_id': _get_id(target)}, {'$set': {'name': name}})
    elif (collection.name == "guild") and (not await read(target)):
        await db.guild.insert_one({'_id': _get_id(target)})

    await collection.update_one({'_id': _get_id(target)}, {'$set': {path: value}})


async def add(target, path: str, value: int):
    """
    adds value to target

    Arguments
    ---------
    target
        targeted object to add value
    path: str
        data path in nested dictionary
    value: int
        value to add to target
    """
    data_before = (await read(target, path)) or 0
    await write(target, path, data_before + value)


async def delete(target):
    """
    removes target in DB

    Arguments
    ---------
    target
        targeted object to delete in DB
    """
    await get_collection(target).delete_one({'_id': _get_id(target)})


async def append(target, path: str, value):
    """
    appends value to target data(list)

    Arguments
    ---------
    target
        targeted object to append value
    path: str
        data path in nested dictionary
    value: int
        value to append to target(list)
    """
    await get_collection(target).update_one(
        {'_id': _get_id(target)},
        {
            '$push': {
                path: value
            }
        }
    )
