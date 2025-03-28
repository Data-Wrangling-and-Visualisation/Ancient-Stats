from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


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
    ability_upgrades_arr: List[int] = Field(default_factory=list)
    is_subscriber: bool
    radiant_win: bool
    start_time: int
    duration: int
    cluster: int
    lobby_type: int
    game_mode: int
    is_contributor: bool
    patch: int
    region: Optional[int] = None
    isRadiant: bool
    win: int
    lose: int
    total_gold: int
    total_xp: Optional[int] = None
    kills_per_min: Optional[float] = None
    kda: float
    abandons: int
    benchmarks: PlayerBenchmarks

    @field_validator("total_xp", "kills_per_min", "region", mode="after")
    def handle_null_regen(cls, v):
        if v is None:
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class DetailedMatchData(BaseModel):
    match_id: int
    rating_id: Optional[int] = None
    players: List[PlayerMatchStats]
