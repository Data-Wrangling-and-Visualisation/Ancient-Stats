class Against:
    def __init__(self, db):
        self.db = db

    async def init(self):
        if await self.db['stats'].find_one({"winrate.against": {'$exists': True}}):
            return
        winrate = {'all': {}}
        async for match in self.db.matches.find({}):
            rating = max(i.get('rank_tier', 0) for i in match['players'])
            rating = str(rating if rating else 43)
            for player_1 in match['players']:
                for player_2 in match['players']:
                    if player_1['team_number'] == player_2['team_number']: continue
                    hero_1 = str(player_1['hero_id'])
                    hero_2 = str(player_2['hero_id'])

                    if rating not in winrate:
                        winrate[rating] = {}

                    if hero_1 not in winrate[rating]:
                        winrate[rating][hero_1] = {}
                    if hero_2 not in winrate[rating][hero_1]:
                        winrate[rating][hero_1][hero_2] = [0, 0]
                    if hero_1 not in winrate['all']:
                        winrate['all'][hero_1] = {}
                    if hero_2 not in winrate['all'][hero_1]:
                        winrate['all'][hero_1][hero_2] = [0, 0]

                    winrate[rating][hero_1][hero_2][player_1['win']] += 1
                    winrate['all'][hero_1][hero_2][player_1['win']] += 1

        await self.db['stats'].insert_one({'winrate': {'against': winrate}})

    async def update(self, match):
        rating = max(i.get('rank_tier', 0) for i in match['players'])
        rating = str(rating if rating else 43)
        for player_1 in match['players']:
            for player_2 in match['players']:
                if player_1['team_number'] == player_2['team_number']: continue
                hero_1 = str(player_1['hero_id'])
                hero_2 = str(player_2['hero_id'])

                lw = await self.db['stats'].find_one({f'winrate.against.{rating}.{hero_1}.{hero_2}': {"$exists": True}})
                lw = lw['winrate']['against'][rating][hero_1][hero_2] if lw else [0, 0]
                lw[player_1['win']] += 1

                await self.db['stats'].update_one(
                    {},
                    {'$set': {f'winrate.against.{rating}.{hero_1}.{hero_2}': lw}},
                    upsert=True
                )

    async def get(self, rating, hero_id=None):
        def add(all, rating):
            if type(rating) == list:
                all[0] += rating[0]
                all[1] += rating[1]
                return
            for i in rating:
                add(all[i], rating[i])

        def proc(all):
            if type(all) == list:
                return (all[1] + 3) / (sum(all) + 6)
            return {i: proc(j) for i, j in all.items()}

        winrate = (await self.db['stats'].find_one({'winrate.against': {'$exists': True}}))['winrate']['against']

        rating = str(rating)
        if rating not in winrate: rating = '43'

        add(winrate['all'], winrate[rating])
        winrate = proc(winrate['all'])

        if hero_id: winrate = winrate[str(hero_id)]
        return winrate
