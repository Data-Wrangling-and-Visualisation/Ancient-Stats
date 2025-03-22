import logging

from pydantic import BaseModel
from requests import get

from .match import MatchModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class PlayerModel(BaseModel):
    id_: int
    name: str
    avatar: str
    steam: str
    rank: int
    matches: list[MatchModel]

    class Config:
        populate_by_name = True


class Player:
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
