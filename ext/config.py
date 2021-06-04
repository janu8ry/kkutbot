import json
import os
from typing import Optional, Union

import yaml

with open('config.yml', encoding='utf-8') as f:
    config_data = yaml.load(f, Loader=yaml.FullLoader)

for file in os.listdir('general'):
    if file not in ("wordlist.json", "DUlaw.json", "quest.json"):
        with open(f"general/{file}", 'r', encoding="utf-8") as f:
            config_data[file[:-5]] = json.load(f)


def get_nested_dict(data, path: list):
    """get value in nested dictionary"""
    for i in path:
        data = data.get(i, None)
    return data


def config(query: Optional[str] = None) -> Union[str, int, dict, list]:
    if not query:
        return config_data
    else:
        return get_nested_dict(config_data, query.split('.'))
