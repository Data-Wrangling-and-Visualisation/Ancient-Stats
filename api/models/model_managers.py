from .match_model import DetailedMatchData, MatchModel
from .heros_model import HeroModel, HeroCollection
from .player_model import PlayerModel

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import logging
from requests import get
import httpx
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from api.utils.errors import (
    Result,
    Err,
    Ok,
    error_handler,
    ErrPlayerIdNotFound,
    ErrDataLoadingFailed,
    ErrInternal,
    ErrHttpxRequest,
)

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
    async def _fetch_match_data(self, match_id: int) -> DetailedMatchData:
        try:
            response = await self.client.get(f"/matches/{match_id}")
            response.raise_for_status()
            return Ok(DetailedMatchData(**response.json()))
        except httpx.HTTPStatusError as e:
            return ErrHttpxRequest(f"API request failed: {e}")
        except Exception as e:
            return ErrInternal(f"Unexpected error fetching match {match_id}: {e}")

    @error_handler
    async def get_match(self, match_id: int) -> DetailedMatchData:
        cached = await self.db.matches.find_one(
            {"match_id": match_id}, projection={"_id": False}
        )
        if cached:
            return Ok(DetailedMatchData(**cached))

        res = await self._fetch_match_data(match_id)
        if not isinstance(res, Ok):
            return res

        match_data, _ = res
        try:
            await self.db.matches.update_one(
                {"match_id": match_id}, {"$set": match_data.model_dump()}, upsert=True
            )
        except DuplicateKeyError:
            pass
        return Ok(match_data)

    @error_handler
    def save_match(self, match_id, json):
        try:
            self.db.matches.update_one(
                {"match_id": match_id},
                {"$set": DetailedMatchData(**json).model_dump()},
                upsert=True,
            )
            return Ok(None)
        except DuplicateKeyError:  # TODO
            logger.error(f"DuplicateKeyError at {self.save_match.__name__}")

        return Err()


class HeroManager:
    _instance = None
    API_URL = "https://api.opendota.com/api/heroStats"

    def __new__(cls, db):
        if cls._instance is None:
            cls._instance = super(HeroManager, cls).__new__(cls)
            cls._instance.db = db
            cls._instance.initialized = False
        return cls._instance

    @error_handler
    async def initialize(self):
        if self.initialized:
            return self.initialized

        if await self.db.heroes.count_documents({}) == 0:
            await self._load_hero_data()
        self.initialized = True

        return Ok(self.initialized)

    @error_handler
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
            return Ok(None)
        except Exception as e:
            print(f"Error loading hero data: {e}")
            return ErrInternal(str(e))

    @error_handler
    async def get_all_heroes(self) -> HeroCollection:
        try:
            heroes = await self.db.heroes.find().to_list(length=None)
            return Ok(HeroCollection(heroes=heroes))
        except Exception as e:
            return ErrInternal(f"Error getting heroes: {e}")

    @error_handler
    async def get_hero(self, hero_id: int) -> HeroModel:
        try:
            hero = await self.db.heroes.find_one({"id": hero_id})
            if not hero:
                return Err(f"Hero {hero_id} not found")
            return Ok(HeroModel(**hero))
        except Exception as e:
            return Err(f"Error getting hero {hero_id}: {e}")


class PlayerManager:
    def __init__(self, id: int, db):
        self.id = id
        self.db = db

        self.player_data = None

        if type(self.id) is not int:
            self.id = None

    @error_handler
    async def load(self) -> Result:
        """
        Loads data about player from DB, if not found, tries to update with API requests
        """
        if self.id is None:
            return ErrPlayerIdNotFound()

        player_data = await self.db.players.find_one({"id_": self.id})
        if not player_data:
            logger.info(f"Player with id {self.id} not found in the database")

            res = await self.update()

            if isinstance(res, ErrDataLoadingFailed):
                return res
            if isinstance(res, ErrPlayerIdNotFound):
                return res

            if not isinstance(res, Ok):
                return res

        self.player_data = PlayerModel(**player_data)
        logger.info(f"Loaded player data of user: {self.id}")

        return Ok(None)

    @error_handler
    def get_matches(self, start=0, end=20) -> Result:
        if not self.player_data:
            return ErrDataLoadingFailed("Player data not loaded: get_matches")

        start_ = max(start, 0)

        if end != -1:
            start_, end = min(start_, end), max(start_, end)

        end_ = min(end, len(self.player_data.matches) - 1)

        res = self.player_data.matches[start_:end_] if self.player_data else []
        return Ok(res)

    @error_handler
    async def update(self) -> Result:
        player_data = get(f"https://api.opendota.com/api/players/{self.id}")
        if player_data.status_code != 200:
            return ErrPlayerIdNotFound()

        match_data = get(f"https://api.opendota.com/api/players/{self.id}/matches")
        if match_data.status_code != 200:
            return ErrDataLoadingFailed(
                f"Failed to get mathc_data: {self.update.__name__=} "
            )

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

        return Ok(None)
