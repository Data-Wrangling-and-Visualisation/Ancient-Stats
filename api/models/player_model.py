from pydantic import BaseModel

from .match_model import MatchModel


class PlayerModel(BaseModel):
    id_: int
    name: str
    avatar: str
    steam: str
    rank: int
    matches: list[MatchModel]

    class Config:
        populate_by_name = True
