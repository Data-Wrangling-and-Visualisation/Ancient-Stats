class XPM:
    def __init__(self, db):
        self.db = db

    async def init(self):
        if await self.db['stats'].find_one({"xpm": {'$exists': True}}):
            return
        xpm = {}
        async for match in self.db.matches.find({}):
            rating = max(i.get('rank_tier', 0) for i in match['players'])
            rating = str(rating if rating else 43)
            for player in match['players']:
                hero_id = str(player['hero_id'])
                if rating not in xpm:
                    xpm[rating] = {}
                if hero_id not in xpm[rating]:
                    xpm[rating][hero_id] = [0, 0]
                xpm[rating][hero_id][0] += player['benchmarks']['xp_per_min']['raw']
                xpm[rating][hero_id][1] += 1
        await self.db['stats'].insert_one({'xpm': xpm})

    async def update(self, match):
        rating = max(i.get('rank_tier', 0) for i in match['players'])
        rating = str(rating if rating else 43)
        for player in match['players']:
            hero_id = str(player['hero_id'])
            wl = await self.db['stats'].find_one({f'xpm.{rating}.{hero_id}': {"$exists": True}})
            wl = wl['xpm'][rating][hero_id] if wl else [0, 0]
            wl[0] += player['benchmarks']['xp_per_min']['raw']
            wl[1] += 1
            await self.db['stats'].update_one(
                {},
                {'$set': {f'xpm.{rating}.{hero_id}': wl}},
                upsert=True
            )

    async def get(self, rating, hero_id=None):
        def proc(xpm):
            if type(xpm) == list:
                return xpm[0] / xpm[1]
            return {i: proc(j) for i, j in xpm.items()}

        rating = str(rating)
        xpm = (await self.db['stats'].find_one({'xpm': {'$exists': True}}))['xpm'][rating]
        if hero_id: xpm = xpm[str(hero_id)]
        return proc(xpm)
