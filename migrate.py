import os
import pickle
import shutil

from ext.config import config
from ext.db import db


def get_winrate(target: dict, _mode: str) -> float:
    game_times = target['game'][_mode]['times']
    game_win_times = target['game'][_mode]['win']
    if 0 in (game_times, game_win_times):
        return 0
    else:
        return round(game_win_times / game_times * 100, 2)


def get_tier(target: dict, _mode: str) -> str:
    if _mode not in ("rank_solo", "rank_multi"):
        raise TypeError
    tier = "언랭크"
    for k, v in config('tierlist').items():  # noqa
        if target['points'] >= v['points'] and get_winrate(target, _mode) >= v['winrate'] and target['game'][_mode]['times'] >= v['times']:
            tier = f"{k} {v['emoji']}"
        else:
            break
    return tier.split(" ")[0]


os.mkdir('backup')


db.user.drop()
ls = []
for i in os.listdir('data/user'):
    with open(f"data/user/{i}", "rb") as f:  # noqa
        data = pickle.load(f)
        data['_id'] = int(str(i).replace('.bin', ''))
        data['_name'] = data['cache']['name']
        del data['cache']
        if 'medal' in data:
            del data['medal']
        if 'token' in data:
            del data['token']
        data['medals'] = 0
        if 'commands' in data:
            del data['commands']
        data['quest'] = {
            'status': {
                'date': 0,
                'completed': []
            },
            'cache': {}
        }
        for mode in config('modelist').values():
            data['game'][mode]['winrate'] = get_winrate(data, mode)
        data['game']['rank_solo']['tier'] = get_tier(data, 'rank_solo')
        data['game']['rank_multi']['tier'] = "언랭크"
        ls.append(data)
db.user.insert_many(ls)

db.guild.drop()
ls = []
for i in os.listdir('data/guild'):
    with open(f"data/guild/{i}", "rb") as f:
        data = pickle.load(f)
        data['_id'] = int(str(i).replace('.bin', ''))
        if 'commands' in data:
            del data['commands']
        ls.append(data)
db.guild.insert_many(ls)

db.unused.drop()
ls = []
for i in os.listdir('data/unused'):
    with open(f"data/unused/{i}", "rb") as f:  # noqa
        data = pickle.load(f)
        data['_id'] = int(str(i).replace('.bin', ''))
        data['_name'] = data['cache']['name']
        del data['cache']
        if 'medal' in data:
            del data['medal']
        if 'token' in data:
            del data['token']
        data['medals'] = 0
        if 'commands' in data:
            del data['commands']
        data['quest'] = {
            'status': {
                'date': 0,
                'completed': []
            },
            'cache': {}
        }
        for mode in config('modelist').values():
            data['game'][mode]['winrate'] = get_winrate(data, mode)
        data['game']['rank_solo']['tier'] = get_tier(data, 'rank_solo')
        data['game']['rank_multi']['tier'] = "언랭크"
        ls.append(data)
db.unused.insert_many(ls)

# db.hanmaru.drop()
# ls = []
# for i in os.listdir('data/hanmaru'):
#     with open(f"data/hanmaru/{i}", "rb") as f:
#         data = pickle.load(f)
#         data['_id'] = data['cached']['id']
#         ls.append(data)
# db.hanmaru.insert_many(ls)

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
data['quest'] = {
    'points': {
        'name': "첫 퀘스트! 10 포인트 모으기",
        'target': 10,
        'reward': (2, 'medals')
    },
    'game/rank_solo/times': {
        'name': "솔로 게임 한판 하기",
        'target': 1,
        'reward': (3, 'medals')
    }
}
db.general.insert_one(data)
shutil.rmtree('./data')
