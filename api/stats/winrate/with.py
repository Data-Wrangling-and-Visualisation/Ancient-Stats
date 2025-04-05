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
                    hero_id = str(player['hero_id'])
                    lvl = str(player['level'])

                    if rating not in winrate:
                        winrate[rating] = {}

                    if hero_id not in winrate[rating]:
                        winrate[rating][hero_id] = {}

                    if lvl not in winrate[rating][hero_id]:
                        winrate[rating][hero_id][lvl] = [0, 0]

                    winrate[rating][hero_id][lvl][player['win']] += 1

        await self.db['stats'].insert_one({'winrate': {'with': winrate}})

    async def update(self, match):
        rating = str(match['rating_id'])
        for player in match['players']:
            hero_id = str(player['hero_id'])
            lvl = str(player['level'])

            lw = await self.db['stats'].find_one({f'winrate.with.{rating}.{hero_id}.{lvl}': {"$exists": True}})
            lw = lw['winrate']['with'][rating][hero_id][lvl] if lw else [0, 0]
            lw[player['win']] += 1

            await self.db['stats'].update_one(
                {},
                {'$set': {f'winrate.with.{rating}.{hero_id}.{lvl}': lw}},
                upsert=True
            )

    async def get(self, rating):
        rating = str(rating)
        hero_id = str(hero_id)
        winrate = (await self.db['stats'].find_one({'winrate.with': {'$exists': True}}))['winrate']['with'][rating][
            hero_id]
        winrate = {i: j[1] / sum(j) for i, j in winrate.items()}
        return winrate
