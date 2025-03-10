from requests import get
from os import listdir
from json import load, dump

players = {i[:-5] for i in listdir('data/users')}


class Player:
    def __init__(self, id):
        self.id = id
        if id not in players:
            self.update()
        with open(f'data/users/{id}.json') as f:
            data = load(f)
        self.name = data['name']
        self.avatar = data['avatar']
        self.steam = data['steam']
        self.rank = data['rank']
        self.matches = data['matches']

    def get_matches(self, start=0, end=20):
        return self.matches[start:end]

    def update(self):
        data = get(f'https://api.opendota.com/api/players/{self.id}').json()
        self.name = data['profile']['personaname']
        self.avatar = data['profile']['avatarfull']
        self.steam = data['profile']['profileurl']
        self.rank = data['rank_tier']
        data = get(f'https://api.opendota.com/api/players/{self.id}/matches').json()
        self.matches = [{
            'id': match['match_id'],
            'win': match['radiant_win'] and match['player_slot'] < 100,
            'duration': match['duration'],
            'game_mode': match['game_mode'],
            'hero_id': match['hero_id'],
            'time': match['start_time'],
            'kills': match['kills'],
            'deaths': match['deaths'],
            'assists': match['assists']
        } for match in data]
        data = {i: getattr(self, i) for i in ('name', 'avatar', 'steam', 'rank', 'matches')}
        with open(f'data/users/{self.id}.json', 'w') as f:
            dump(data, f)
