import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Self,
    TypeVar,
    cast,
)

import httpx
import requests
from pymongo.errors import DuplicateKeyError
from pymongo.results import UpdateResult
from requests import get
from tenacity import retry, stop_after_attempt, wait_exponential

from api.utils.errors import (
    Err,
    ErrDataLoadingFailed,
    ErrHttpxRequest,
    ErrInternal,
    ErrPlayerIdNotFound,
    Ok,
    error_handler,
)
from api.models.general_model import DotaDatabase
from api.models.heros_model import HeroCollection, HeroModel
from api.models.match_model import DetailedMatchData, MatchModel
from api.models.player_model import PlayerModel

logger = logging.getLogger(__name__)

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


class MatchManager:
    """
    Manages match data from the OpenDota API.
    """

    API_BASE_URL = "https://api.opendota.com/api"

    def __init__(self, db: DotaDatabase) -> None:
        """
        Initializes the MatchManager with a database connection.

        Args:
            db (DotaDatabase): The database connection.
        """
        self.db = db
        self.client = httpx.AsyncClient(
            base_url=self.API_BASE_URL,
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_connections=100),
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Any,
    ) -> None:
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _fetch_match_data(
        self, match_id: int
    ) -> Ok[DetailedMatchData] | ErrHttpxRequest | ErrInternal:
        try:
            response = await self.client.get(f"/matches/{match_id}")
            response.raise_for_status()
            return Ok(DetailedMatchData(**response.json()))
        except httpx.HTTPStatusError as e:
            return ErrHttpxRequest(f"API request failed: {e}")
        except Exception as e:
            return ErrInternal(f"Unexpected error fetching match {match_id}: {e}")

    @error_handler
    async def get_match(
        self, match_id: int
    ) -> Ok[DetailedMatchData] | ErrHttpxRequest | ErrInternal:
        """
        Fetches match data from the OpenDota API.

        Args:
            match_id (int): The ID of the match to fetch.

        Returns:
            Ok[DetailedMatchData]

        Returned Errors:
            ErrHttpxRequest: If the API request fails.
            ErrInternal: If an unexpected error occurs.
        """
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
            update_result = await self.db.matches.update_one(
                {"match_id": match_id}, {"$set": match_data.model_dump()}, upsert=True
            )
            if not isinstance(update_result, UpdateResult):
                return ErrInternal("Failed to update match data")
        except DuplicateKeyError:
            pass
        return Ok(match_data)

    @error_handler
    async def save_match(
        self, match_id: int, json: Dict[str, Any]
    ) -> Ok[None] | Err[Any]:
        """
        Saves match data to the database.

        Args:
            match_id (int): The ID of the match to save.
            json (Dict[str, Any]): The match data to save.

        Returns:
            Ok[None]

        Returned Errors:
            Err[Any]: If an error occurs.
        """

        try:
            await self.db.matches.update_one(
                {"match_id": match_id},
                {"$set": DetailedMatchData(**json).model_dump()},
                upsert=True,
            )
            return Ok(None)
        except DuplicateKeyError:  # TODO
            logger.error(f"DuplicateKeyError at {self.save_match.__name__}")

        return Err()


class HeroManager:
    """
    Manages hero data from the OpenDota API.

    Singleton class.
    """

    _instance: Optional["HeroManager"] = None
    API_URL = "https://api.opendota.com/api/heroStats"
    db: DotaDatabase
    initialized: bool

    def __new__(cls, db: DotaDatabase) -> "HeroManager":
        if cls._instance is None:
            cls._instance = super(HeroManager, cls).__new__(cls)
            cls._instance.db = db
            cls._instance.initialized = False
        return cls._instance

    @error_handler
    async def initialize(self) -> Ok[bool]:
        """
        Initializes the HeroManager.

        Returns:
            Ok[bool]: True if the HeroManager is initialized, False otherwise.
        """
        if self.initialized:
            return Ok(self.initialized)

        count = await self.db.heroes.count_documents({})
        if count == 0:
            await self._load_hero_data()
        self.initialized = True

        return Ok(self.initialized)

    @error_handler
    async def _load_hero_data(self) -> Ok[None] | ErrInternal:
        try:
            response = requests.get(self.API_URL)
            response.raise_for_status()
            hero_data = response.json()

            heroes: List[Dict[str, Any]] = []
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
    async def get_all_heroes(self) -> Ok[HeroCollection] | ErrInternal | Err[Any]:
        """
        Fetches all heroes from the database.

        Returns:
            Ok[HeroCollection]

        Returned Errors:
            ErrInternal: If an error occurs in the database.
        """
        try:
            heroes = await self.db.heroes.find().to_list(length=None)
            return Ok(HeroCollection(heroes=heroes))
        except Exception as e:
            return ErrInternal(f"Error getting heroes: {e}")

    @error_handler
    async def get_hero(self, hero_id: int) -> Ok[HeroModel] | Err[Any]:
        """
        Fetches a hero from the database.

        Args:
            hero_id (int): The ID of the hero to fetch.

        Returns:
            Ok[HeroModel]

        Returned Errors:
            Err[Any]: If an unexpected error occurs.
        """
        try:
            hero = await self.db.heroes.find_one({"id": hero_id})
            if not hero:
                logger.error(f"Hero {hero_id} not found")
                return Err()
            return Ok(HeroModel(**hero))
        except Exception as e:
            logger.error(f"Error getting hero {hero_id}: {e}")
            return Err()


class PlayerManager:
    """
    Manages player data from the OpenDota API.
    """

    def __init__(self, id: int, db: DotaDatabase) -> None:
        self.id = id
        self.db = db
        self.player_data: Optional[PlayerModel] = None

        if not isinstance(self.id, int):
            self.id = None

    @error_handler
    async def load(
        self,
    ) -> Ok[None] | ErrPlayerIdNotFound | ErrDataLoadingFailed | Err[Any]:
        """
        Loads data about player from DB, if not found, tries to update with API requests

        Returns:
            Ok[None]: Background task - data will be loaded in the class variables.

        Returned Errors:
            ErrPlayerIdNotFound: If the player ID is not found.
            ErrDataLoadingFailed: If the data loading fails.
        """
        if self.id is None:
            return ErrPlayerIdNotFound()

        player_data: Optional[Dict[str, Any]] = await self.db.players.find_one(
            {"id_": self.id}
        )
        if not player_data:
            logger.info(f"Player with id {self.id} not found in the database")

            res = await self.update()

            if isinstance(res, ErrDataLoadingFailed):
                return res
            if isinstance(res, ErrPlayerIdNotFound):
                return res

            if isinstance(res, Err):
                return res  # type: ignore

        self.player_data = PlayerModel(**player_data)  # type: ignore
        logger.info(f"Loaded player data of user: {self.id}")

        return Ok(None)

    @error_handler
    def get_matches(
        self, start: int = 0, end: int = 20
    ) -> Ok[List[MatchModel]] | ErrDataLoadingFailed:
        """
        Fetches matches from the player's data.

        Args:
            start (int): The start index of the matches to fetch.
            end (int): The end index of the matches to fetch.

        Returns:
            Ok[List[MatchModel]]

        Returned Errors:
            ErrDataLoadingFailed: If the data loading fails.
        """

        if not self.player_data:
            return ErrDataLoadingFailed("Player data not loaded: get_matches")

        start_ = max(start, 0)

        if end != -1:
            start_, end = min(start_, end), max(start_, end)

        end_ = min(end, len(self.player_data.matches) - 1)

        res = self.player_data.matches[start_:end_] if self.player_data else []
        return Ok(res)

    @error_handler
    async def update(
        self,
    ) -> Ok[None] | ErrDataLoadingFailed | ErrPlayerIdNotFound | Err[Any]:
        """
        Updates the player's data.

        Returns:
            Ok[None]

        Returned Errors:
            ErrPlayerIdNotFound: If the player ID is not found.
            ErrDataLoadingFailed: If the data loading fails.
            Err[Any]: If an unexpected error occurs.
        """
        player_data = get(f"https://api.opendota.com/api/players/{self.id}")
        if player_data.status_code != 200:
            return ErrPlayerIdNotFound()

        match_data = get(f"https://api.opendota.com/api/players/{self.id}/matches")
        if match_data.status_code != 200:
            return ErrDataLoadingFailed(
                f"Failed to get match_data: {self.update.__name__=} "
            )

        match_data = match_data.json()
        player_data = player_data.json()

        player_model = PlayerModel(
            id_=cast(int, self.id),
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

        update_result = await self.db.players.update_one(
            {"id_": cast(int, self.id)},
            {"$set": player_model.model_dump()},
            upsert=True,
        )

        self.player_data = player_model.model_copy()

        logger.info(f"Updated player data of user: {self.id}")

        return Ok(None)
