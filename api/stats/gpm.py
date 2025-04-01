class Gpm:
    def __init__(self, db):
        self.db = db
    async def init(self):
        if await self.db['stats'].find_one({"gpm": {'$exists': True}}):
            return
        gpm = {}
        async for match in self.db.matches.find({}):
            rating = str(match['rating_id'])
            for player in match['players']:
                hero_id = str(player['hero_id'])
                if hero_id not in gpm:
                    gpm[hero_id] = {}
                if rating not in gpm[hero_id]:
                    gpm[hero_id][rating] = [0, 0]
                gpm[hero_id][rating][0] += player['benchmarks']['gold_per_min']['raw']
                gpm[hero_id][rating][1] += 1
        for hero_id in gpm:
            gpm[hero_id]['upd'] = True
        await self.db['stats'].drop()
        await self.db['stats'].insert_one({'gpm': {'real': gpm}})

    async def update(self, match):
        rating = str(match['rating_id'])
        for player in match['players']:
            hero_id = str(player['hero_id'])
            wl = await self.db['stats'].find_one({f'gpm.real.{hero_id}.{rating}': {"$exists": True}})
            if wl:
                wl = wl['gpm']['real'][hero_id][rating]
            else:
                wl = [0, 0]
            wl[0] += player['benchmarks']['gold_per_min']['raw']
            wl[1] += 1
            await self.db['stats'].update_one(
                {},
                {'$set': {f'gpm.real.{hero_id}.upd': True}},
                upsert=True
            )
            await self.db['stats'].update_one(
                {},
                {'$set': {f'gpm.real.{hero_id}.{rating}': wl}},
                upsert=True
            )

    async def get_gpm(self, rating):
        winrate = (await self.db['stats'].find_one({'gpm': {'$exists': True}}))['gpm']['real']
        for hero_id in winrate:
            upd = winrate[hero_id].get('upd', False)
            if upd:
                items = tuple(winrate[hero_id].items())
                wl = [wl[0] / wl[1] for rate, wl in items if rate != 'upd']
                for rate, _ in items:
                    if rate == 'upd': continue
                    rate = int(rate)
                    k = [0.8 ** abs(rate - int(rt)) for rt, _ in items if rt != 'upd']
                    wr = sum(w * k for w, k in zip(wl, k)) / sum(k)
                    await self.db['stats'].update_one(
                        {},
                        {'$set': {f'gpm.norm.{hero_id}.{rate}': wr}},
                        upsert=True
                    )
                await self.db['stats'].update_one(
                    {},
                    {'$set': {f'gpm.real.{hero_id}.upd': False}},
                )
        winrate = (await self.db['stats'].find_one())['gpm']['norm']
        rating = str(rating)
        return {hero_id: wr.get(rating, 0) for hero_id, wr in winrate.items()}