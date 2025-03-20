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
    def __init__(self, id, db):
        self.id: str = id
        self.db = db

        self.player_data = None

    async def load(self) -> None:
        player_data = await self.db.players.find_one({"id_": int(self.id)})
        if not player_data:
            logger.error(f"Player with id {self.id} not found.")
            await self.update()
            player_data = await self.db.players.find_one({"id_": int(self.id)})
            if not player_data:
                logger.error(f"Player with id {self.id} still not found after update.")
                self.player_data = None
                return

        self.player_data = PlayerModel(**player_data)
        logger.info(f"Loaded player data: {self.player_data}")

    def get_matches(self, start=0, end=20) -> list[MatchModel] | list:
        return self.player_data.matches[start:end] if self.player_data else []

    async def update(self) -> None:
        player_data = get(f"https://api.opendota.com/api/players/{self.id}")

        if player_data.status_code != 200:
            self.id = None
            return None

        match_data = get(f"https://api.opendota.com/api/players/{self.id}/matches")

        if match_data.status_code != 200:
            return None

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
