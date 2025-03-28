from .match_model import DetailedMatchData, MatchModel
from .heros_model import HeroModel, HeroCollection
from .player_model import PlayerModel

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import logging
from requests import get
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MatchManager:
    API_BASE_URL = "https://api.opendota.com/api"

    def __init__(self, db):
        self.db = db
        self.client = httpx.AsyncClient(
            base_url=self.API_BASE_URL,
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_connections=100),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch_match_data(self, match_id: int) -> DetailedMatchData:
        try:
            response = await self.client.get(f"/matches/{match_id}")
            response.raise_for_status()
            return DetailedMatchData(**response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"API error for match {match_id}: {e}")
            raise HTTPException(
                status_code=e.response.status_code, detail="Failed to fetch match data"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching match {match_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_match(self, match_id: int) -> DetailedMatchData:
        if cached := await self.db.matches.find_one(
                {"match_id": match_id}, projection={"_id": False}
        ):
            logger.debug(f"Cache hit for match {match_id}")
            return DetailedMatchData(**cached)

        match_data = await self.fetch_match_data(match_id)

        try:
            await self.db.matches.update_one(
                {"match_id": match_id}, {"$set": match_data.model_dump()}, upsert=True
            )
        except DuplicateKeyError:
            cached = await self.db.matches.find_one(
                {"match_id": match_id}, projection={"_id": False}
            )
            return DetailedMatchData(**cached)

        return match_data

    def save_match(self, match_id, json):
        try:
            self.db.matches.update_one(
                {'match_id': match_id}, {"$set": DetailedMatchData(**json).model_dump()}, upsert=True
            )
        except DuplicateKeyError:
            pass


class HeroManager:
    _instance = None
    API_URL = "https://api.opendota.com/api/heroStats"

    def __new__(cls, db):
        if cls._instance is None:
            cls._instance = super(HeroManager, cls).__new__(cls)
            cls._instance.db = db
            cls._instance.initialized = False
        return cls._instance

    async def initialize(self):
        if self.initialized:
            return self.initialized

        if await self.db.heroes.count_documents({}) == 0:
            await self._load_hero_data()
        self.initialized = True

        return self.initialized

    async def _load_hero_data(self):
        try:
            response = requests.get(self.API_URL)
            response.raise_for_status()
            hero_data = response.json()

            heroes = []
            for hero in hero_data:
                hero["primary_attr"] = {
                    "str": "strength",
                    "agi": "agility",
                    "int": "intelligence",
                    "all": "universal",
                }[hero["primary_attr"]]

                validated_hero = HeroModel(**hero)
                heroes.append(validated_hero.model_dump())

            if heroes:
                await self.db.heroes.insert_many(heroes)
        except Exception as e:
            print(f"Error loading hero data: {e}")
            raise

    async def get_all_heroes(self) -> HeroCollection:
        heroes = await self.db.heroes.find().to_list(length=None)
        return HeroCollection(heroes=heroes)

    async def get_hero(self, hero_id: int) -> HeroModel:
        hero = await self.db.heroes.find_one({"id": hero_id})
        if not hero:
            raise HTTPException(status_code=404, detail="Hero not found")
        return HeroModel(**hero)


class PlayerManager:
    def __init__(self, id: int, db):
        self.id = id
        self.db = db

        self.player_data = None

        if type(self.id) is not int:
            self.id = None

    async def load(self) -> None:
        """
        Loads data about player from DB, if not found, tries to update with API requests
        """
        if self.id is None:
            return {"status": False, "details": "invalid id type"}

        player_data = await self.db.players.find_one({"id_": self.id})
        if not player_data:
            logger.info(f"Player with id {self.id} not found in the database")

            res = await self.update()
            if not res["status"]:
                logger.info(f"Loading data of {self.id} was failed: {res['details']}")
                return {"status": False, "details": "loading data was failed"}

        self.player_data = PlayerModel(**player_data)
        logger.info(f"Loaded player data of user: {self.id}")

        return {"status": True, "details": ""}

    def get_matches(self, start=0, end=20) -> list[MatchModel] | list:
        end_ = min(end, len(self.player_data.matches) - 1)
        return self.player_data.matches[start:end_] if self.player_data else []

    async def update(self) -> None:
        player_data = get(f"https://api.opendota.com/api/players/{self.id}")
        if player_data.status_code != 200:
            return {"status": False, "details": "user_id request was failed"}

        match_data = get(f"https://api.opendota.com/api/players/{self.id}/matches")
        if match_data.status_code != 200:
            return {"status": False, "details": "match_data request was failed"}

        match_data = match_data.json()
        player_data = player_data.json()

        player_model = PlayerModel(
            id_=self.id,
            name=player_data["profile"]["personaname"],
            avatar=player_data["profile"]["avatarfull"],
            steam=player_data["profile"]["profileurl"],
            rank=player_data["rank_tier"],
            matches=[
                MatchModel(
                    **{
                        "id": match["match_id"],
                        "win": match["radiant_win"] and match["player_slot"] < 100,
                        "duration": match["duration"],
                        "game_mode": match["game_mode"],
                        "hero_id": match["hero_id"],
                        "time": match["start_time"],
                        "kills": match["kills"],
                        "deaths": match["deaths"],
                        "assists": match["assists"],
                    }
                )
                for match in match_data
            ],
        )

        await self.db.players.update_one(
            {"id_": int(self.id)}, {"$set": player_model.model_dump()}, upsert=True
        )

        self.player_data = player_model.model_copy()

        logger.info(f"Updated player data of user: {self.id}")

        return {"status": True, "details": "User data was updated"}
