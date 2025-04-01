class Xpm:
    def __init__(self, db):
        self.db = db
    async def init(self):
        if await self.db['stats'].find_one({"xpm": {'$exists': True}}):
            return
        xpm = {}
        async for match in self.db.matches.find({}):
            rating = str(match['rating_id'])
            for player in match['players']:
                hero_id = str(player['hero_id'])
                if hero_id not in xpm:
                    xpm[hero_id] = {}
                if rating not in xpm[hero_id]:
                    xpm[hero_id][rating] = [0, 0]
                xpm[hero_id][rating][0] += player['benchmarks']['xp_per_min']['raw']
                xpm[hero_id][rating][1] += 1
        for hero_id in xpm:
            xpm[hero_id]['upd'] = True
        await self.db['stats'].drop()
        await self.db['stats'].insert_one({'xpm': {'real': xpm}})

    async def update(self, match):
        rating = str(match['rating_id'])
        for player in match['players']:
            hero_id = str(player['hero_id'])
            wl = await self.db['stats'].find_one({f'xpm.real.{hero_id}.{rating}': {"$exists": True}})
            if wl:
                wl = wl['xpm']['real'][hero_id][rating]
            else:
                wl = [0, 0]
            wl[0] += player['benchmarks']['xp_per_min']['raw']
            wl[1] += 1
            await self.db['stats'].update_one(
                {},
                {'$set': {f'xpm.real.{hero_id}.upd': True}},
                upsert=True
            )
            await self.db['stats'].update_one(
                {},
                {'$set': {f'xpm.real.{hero_id}.{rating}': wl}},
                upsert=True
            )

    async def get_xpm(self, rating):
        winrate = (await self.db['stats'].find_one({'xpm': {'$exists': True}}))['xpm']['real']
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
                        {'$set': {f'xpm.norm.{hero_id}.{rate}': wr}},
                        upsert=True
                    )
                await self.db['stats'].update_one(
                    {},
                    {'$set': {f'xpm.real.{hero_id}.upd': False}},
                )
        winrate = (await self.db['stats'].find_one())['xpm']['norm']
        rating = str(rating)
        return {hero_id: wr.get(rating, 0) for hero_id, wr in winrate.items()}