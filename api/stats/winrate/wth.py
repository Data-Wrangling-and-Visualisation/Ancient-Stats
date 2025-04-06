class With:
    def __init__(self, db):
        self.db = db

    async def init(self):
        if await self.db['stats'].find_one({"winrate.with": {'$exists': True}}):
            return
        winrate = {}
        async for match in self.db.matches.find({}):
            rating = str(match['rating_id'])
            for player_1 in match['players']:
                for player_2 in match['players']:
                    if player_1['team_number'] != player_2['team_number']: continue
                    hero_1 = str(player_1['hero_id'])
                    hero_2 = str(player_2['hero_id'])
                    if hero_1 == hero_2: continue

                    if rating not in winrate:
                        winrate[rating] = {}

                    if hero_1 not in winrate[rating]:
                        winrate[rating][hero_1] = {}
                    if hero_2 not in winrate[rating][hero_1]:
                        winrate[rating][hero_1][hero_2] = [0, 0]

                    winrate[rating][hero_1][hero_2][player_1['win']] += 1

        await self.db['stats'].insert_one({'winrate': {'with': winrate}})

    async def update(self, match):
        rating = str(match['rating_id'])
        for player_1 in match['players']:
            for player_2 in match['players']:
                if player_1['team_number'] != player_2['team_number']: continue
                hero_1 = str(player_1['hero_id'])
                hero_2 = str(player_2['hero_id'])

                lw = await self.db['stats'].find_one({f'winrate.with.{rating}.{hero_1}.{hero_2}': {"$exists": True}})
                lw = lw['winrate']['with'][rating][hero_1][hero_2] if lw else [0, 0]
                lw[player_1['win']] += 1

                await self.db['stats'].update_one(
                    {},
                    {'$set': {f'winrate.with.{rating}.{hero_1}.{hero_2}': lw}},
                    upsert=True
                )

    async def get(self, rating, hero_id=None):
        def proc(winrate):
            if type(winrate) == list:
                return winrate[1] / sum(winrate)
            return {i: proc(j) for i, j in winrate.items()}

        rating = str(rating)
        winrate = (await self.db['stats'].find_one({'winrate.with': {'$exists': True}}))['winrate']['with'][rating]
        if hero_id: winrate = winrate[str(hero_id)]
        return proc(winrate)
