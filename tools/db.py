import asyncio
import logging
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal, Optional, Union
from typing_extensions import TypeAlias

from motor.motor_asyncio import AsyncIOMotorClient

try:
    import uvloop
except ImportError:
    uvloop = None

from config import config, get_nested_dict

logger = logging.getLogger("kkutbot")
MODE = "test" if config("test") else "main"

coltype: TypeAlias = Literal["user", "guild", "general", "unused"]


def dbconfig(query: str) -> Any:
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
    return config(f"mongo.{MODE}.{query}")


db_options = {}

if all([username := dbconfig("user"), password := dbconfig("password")]):
    db_options["username"] = username
    db_options["password"] = password

if uvloop:
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
else:
    loop = asyncio.get_event_loop()

_client = AsyncIOMotorClient(
    host=dbconfig("ip"), port=dbconfig("port"), io_loop=loop, **db_options
)

logger.info("mongoDB에 연결됨")


db = _client[dbconfig("db")]


async def read(id_: Union[int, str], col: coltype, path: Optional[str] = None) -> Any:
    """
    reads target info

    Arguments
    ---------
    id_: Union[int, str]
        target id to read info
    col: str
        mongoDB collection to get id
    path: Optional[str]
        data path in nested dictionary

    Returns
    -------
    Any
        target's info
    """
    main_data = await db[col].find_one({"_id": id_})
    if not main_data:
        if col == "user":
            main_data = deepcopy(config("default_data.user"))
        elif col == "guild":
            main_data = deepcopy(config("default_data.guild"))
        elif col == "general":
            main_data = deepcopy(config("default_data.general"))
        else:
            raise ValueError

    if path is None:
        return main_data

    return get_nested_dict(main_data, path.split("."))


async def write(id_: Union[int, str], col: coltype, path: str, value, name: Optional[str] = None):
    """
    writes value to target

    Arguments
    ---------
    id_: Union[int, str]
        target id to read info
    col: str
        mongoDB collection to get id
    path: Optional[str]
        data path in nested dictionary
    value
        value to write into DB
    name: Optional[str]
        name of user when col == "user"
    """

    if col == "user":
        if not (await read(id_, "user", "registered")):
            if data := await db.unused.find_one({"_id": id_}):
                await db.user.insert_one(data)
                await db.unused.delete_one({"_id": id_})
            else:
                main_data = await read(id_, "user")
                main_data["register_date"] = datetime.now()
                main_data["_id"] = id_
                main_data["name"] = name
                await db.user.insert_one(main_data)
        if name and name != (await read(id_, "user", "name")):
            await db.user.update_one({"_id": id_}, {"$set": {"name": name}})
    elif (col == "guild") and (await read(id_, "guild") == deepcopy(config("default_data.guild"))):
        main_data = await read(id_, "guild")
        main_data["invited"] = datetime.now()
        main_data["_id"] = id_
        await db.guild.insert_one(main_data)

    await db[col].update_one({"_id": id_}, {"$set": {path: value}})


async def delete(id_: Union[int, str], col: coltype):
    """
    removes target in DB

    Arguments
    ---------
    id_: Union[int, str]
        target id to read info
    col: str
        mongoDB collection to get id
    """
    await db[col].delete_one({"_id": id_})
