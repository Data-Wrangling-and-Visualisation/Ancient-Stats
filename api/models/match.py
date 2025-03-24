from pydantic import BaseModel


class MatchModel(BaseModel):
    id: int
    win: bool
    duration: int
    game_mode: int
    hero_id: int
    time: int
    kills: int
    deaths: int
    assists: int
