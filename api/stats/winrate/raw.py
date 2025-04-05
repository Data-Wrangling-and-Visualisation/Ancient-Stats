class Raw:
    def __init__(self, db):
        self.db = db

    async def init(self):
        print('zxc')
        if await self.db['stats'].find_one({"winrate.raw": {'$exists': True}}):
            return
        winrate = {}
        async for match in self.db.matches.find({}):
            rating = str(match['rating_id'])
            for player in match['players']:
                hero_id = str(player['hero_id'])

                if rating not in winrate:
                    winrate[rating] = {}

                if hero_id not in winrate[rating]:
                    winrate[rating][hero_id] = [0, 0]

                winrate[rating][hero_id][player['win']] += 1
        await self.db['stats'].insert_one({'winrate': {'raw': winrate}})

    async def update(self, match):
        rating = str(match['rating_id'])
        for player in match['players']:
            hero_id = str(player['hero_id'])

            lw = await self.db['stats'].find_one({f'winrate.raw.{rating}.{hero_id}': {"$exists": True}})
            lw = lw['winrate']['raw'][rating][hero_id] if lw else [0, 0]
            lw[player['win']] += 1

            await self.db['stats'].update_one(
                {},
                {'$set': {f'winrate.raw.{rating}.{hero_id}': lw}},
                upsert=True
            )

    async def get(self, rating):
        rating = str(rating)
        winrate = (await self.db['stats'].find_one({'winrate.raw': {'$exists': True}}))['winrate']['raw'][rating]
        winrate = {i: j[1] / sum(j) for i, j in winrate.items()}
        return winrate
