import json
import os
from typing import List, Any

import yaml

with open('config.yml', encoding='utf-8') as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

for file in os.listdir('data'):
    if file not in ("wordlist.json", "DUlaw.json", "quest.json"):
        with open(f"data/{file}", 'r', encoding='utf-8') as f:
            config_data[file[:-5]] = json.load(f)


def get_nested_dict(data: dict, path: List[str]) -> Any:
    """
    gets value in nested dictionary.
    Parameters
    ----------
    data : dict
        Target dictionary to get value
    path : list[str]
        list of keys to get value
    Returns
    -------
    Any
        value in targeted dictionary
    """
    for i in path:
        data = data.get(i, None)
    return data


def get_nested_property(data: Any, path: List[str]) -> Any:
    """
    gets property in nested dataclass.
    Parameters
    ----------
    data : Any
        Target dataclass to get value
    path : list[str]
        list of properties to get value
    Returns
    -------
    Any
        value in targeted dataclass
    """
    for i in path:
        data = data.getattr(i, None)
    return data


def config(query: str) -> Any:
    """
    gets value in 'config.yml' file
    Parameters
    ----------
    query : str
    Returns
    -------
    Any
        value in 'config.yml' file
    """
    if not query:
        return config_data
    else:
        return get_nested_dict(config_data, query.split('.'))
