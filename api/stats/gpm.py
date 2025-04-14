class GPM:
    def __init__(self, db):
        self.db = db

    async def init(self):
        if await self.db['stats'].find_one({"gpm": {'$exists': True}}):
            return
        gpm = {}
        async for match in self.db.matches.find({}):
            rating = max(i.get('rank_tier', 0) for i in match['players'])
            rating = str(rating if rating else 43)
            for player in match['players']:
                hero_id = str(player['hero_id'])
                if rating not in gpm:
                    gpm[rating] = {}
                if hero_id not in gpm[rating]:
                    gpm[rating][hero_id] = [0, 0]
                gpm[rating][hero_id][0] += player['benchmarks']['gold_per_min']['raw']
                gpm[rating][hero_id][1] += 1
        await self.db['stats'].insert_one({'gpm': gpm})

    async def update(self, match):
        rating = max(i.get('rank_tier', 0) for i in match['players'])
        rating = str(rating if rating else 43)
        for player in match['players']:
            hero_id = str(player['hero_id'])
            wl = await self.db['stats'].find_one({f'gpm.{rating}.{hero_id}': {"$exists": True}})
            wl = wl['gpm'][rating][hero_id] if wl else [0, 0]
            wl[0] += player['benchmarks']['gold_per_min']['raw']
            wl[1] += 1
            await self.db['stats'].update_one(
                {},
                {'$set': {f'gpm.{rating}.{hero_id}': wl}},
                upsert=True
            )

    async def get(self, rating, hero_id=None):
        def proc(gpm):
            if type(gpm) == list:
                return gpm[0] / gpm[1]
            return {i: proc(j) for i, j in gpm.items()}

        rating = str(rating)
        gpm = (await self.db['stats'].find_one({'gpm': {'$exists': True}}))['gpm'][rating]
        if hero_id: gpm = gpm[str(hero_id)]
        return proc(gpm)
