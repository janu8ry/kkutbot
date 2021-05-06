import os
import pickle

from ext.config import config
from ext.db import db
from ext.utils import get_tier, get_winrate

os.mkdir('backup')

db.user.drop()
for i in os.listdir('data/user'):
    ls = []
    with open(f"data/user/{i}", "rb") as f:
        data = pickle.load(f)
        data['_id'] = data['cache']['id']
        data['_name'] = data['cache']['name']
        del data['cache']
        if 'commands' in data:
            del data['commands']
        data['game']['rank_solo']['tier'] = get_tier(int(str(i).replace('.bin', '')), 'rank_solo', emoji=False)
        data['game']['rank_multi']['tier'] = "언랭크"
        for mode in config('modelist').values():
            data['game'][mode]['winrate'] = get_winrate(int(str(i).replace('.bin', '')), mode)
        ls.append(data)
    db.user.insert_many(ls)

db.guild.drop()
for i in os.listdir('data/guild'):
    ls = []
    with open(f"data/guild/{i}", "rb") as f:
        data = pickle.load(f)
        data['_id'] = int(str(i).replace('.bin', ''))
        if 'commands' in data:
            del data['commands']
        ls.append(data)
    db.guild.insert_many(ls)

db.unused.drop()
for i in os.listdir('data/unused'):
    ls = []
    with open(f"data/unused/{i}", "rb") as f:
        data = pickle.load(f)
        data['_id'] = int(str(i).replace('.bin', ''))
        data['_name'] = data['cache']['name']
        del data['cache']
        data['game']['rank_solo']['tier'] = get_tier(int(str(i).replace('.bin', '')), 'rank_solo', emoji=False)
        data['game']['rank_multi']['tier'] = "언랭크"
        ls.append(data)
    db.unused.insert_many(ls)

db.hanmaru.drop()
for i in os.listdir('data/hanmaru'):
    ls = []
    with open(f"data/hanmaru/{i}", "rb") as f:
        data = pickle.load(f)
        data['_id'] = data['cached']['id']
        ls.append(data)
    db.hanmaru.insert_many(ls)

db.general.drop()
with open('data/public/general.bin', 'rb') as f:
    data = pickle.load(f)
with open('data/public/commands.bin', 'rb') as f:
    command_data = pickle.load(f)
    for k, v in command_data.copy().items():
        if k.startswith('$'):
            command_data[k.replace('$', '_')] = v
            del command_data[k]
data['commands'] = command_data
data['_id'] = "general"
db.general.insert_one(data)
