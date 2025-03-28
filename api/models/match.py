from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class BenchmarkStats(BaseModel):
    raw: float
    pct: float


class PlayerBenchmarks(BaseModel):
    gold_per_min: BenchmarkStats
    xp_per_min: BenchmarkStats
    kills_per_min: BenchmarkStats
    last_hits_per_min: BenchmarkStats
    hero_damage_per_min: BenchmarkStats
    hero_healing_per_min: BenchmarkStats
    tower_damage: BenchmarkStats


class PlayerMatchStats(BaseModel):
    player_slot: int
    team_number: int
    team_slot: int
    hero_id: int
    hero_variant: Optional[int] = None
    item_0: int
    item_1: int
    item_2: int
    item_3: int
    item_4: int
    item_5: int
    backpack_0: Optional[int] = None
    backpack_1: Optional[int] = None
    backpack_2: Optional[int] = None
    item_neutral: Optional[int] = None
    item_neutral2: Optional[int] = None
    kills: int
    deaths: int
    assists: int
    leaver_status: int
    last_hits: int
    denies: int
    gold_per_min: int
    xp_per_min: int
    level: int
    net_worth: int
    aghanims_scepter: int
    aghanims_shard: int
    moonshard: int
    hero_damage: int
    tower_damage: int
    hero_healing: int
    gold: int
    gold_spent: int
    ability_upgrades_arr: List[int]
    is_subscriber: bool
    radiant_win: bool
    start_time: int
    duration: int
    cluster: int
    lobby_type: int
    game_mode: int
    is_contributor: bool
    patch: int
    region: int
    isRadiant: bool
    win: int
    lose: int
    total_gold: int
    total_xp: int
    kills_per_min: float
    kda: float
    abandons: int
    benchmarks: PlayerBenchmarks


class DetailedMatchData(BaseModel):
    match_id: int
    rating_id: Optional[int] = None
    players: List[PlayerMatchStats]
    created_at: datetime = Field(default_factory=datetime.now(datetime.timezone.utc))
    updated_at: datetime = Field(default_factory=datetime.now(datetime.timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.timestamp()}

from motor.motor_asyncio import AsyncIOMotorClient
from models import MatchData
from typing import List, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class MatchManager:
    def __init__(self, db):
        self.db = db
        self.collection = db.matches

    async def create_match(self, match_data: MatchData):
        try:
            result = await self.collection.insert_one(match_data.dict())
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            raise HTTPException(status_code=500, detail="Failed to create match")

    async def get_match(self, match_id: int) -> Optional[MatchData]:
        try:
            match = await self.collection.find_one({"match_id": match_id})
            if match:
                return MatchData(**match)
            return None
        except Exception as e:
            logger.error(f"Error getting match {match_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get match")

    async def get_matches_by_rating(self, rating_id: int) -> List[MatchData]:
        try:
            matches = await self.collection.find({"rating_id": rating_id}).to_list(None)
            return [MatchData(**match) for match in matches]
        except Exception as e:
            logger.error(f"Error getting matches for rating {rating_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get matches")

    async def update_match(self, match_id: int, update_data: dict):
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = await self.collection.update_one(
                {"match_id": match_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating match {match_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update match")

    async def delete_match(self, match_id: int):
        try:
            result = await self.collection.delete_one({"match_id": match_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting match {match_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete match")