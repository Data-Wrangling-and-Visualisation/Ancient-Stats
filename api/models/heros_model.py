from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class PrimaryAttribute(str, Enum):
    strength = "strength"
    agility = "agility"
    intelligence = "intelligence"
    universal = "universal"


class AttackType(str, Enum):
    melee = "Melee"
    ranged = "Ranged"


class HeroModel(BaseModel):
    id: int
    name: str
    primary_attr: PrimaryAttribute
    attack_type: AttackType
    roles: List[str]
    img: str
    icon: str
    base_health: int
    base_health_regen: float = Field(default=0.0)
    base_mana: int
    base_mana_regen: float = Field(default=0.0)
    base_armor: int
    base_mr: int
    base_attack_min: int
    base_attack_max: int
    base_str: int
    base_agi: int
    base_int: int
    str_gain: float
    agi_gain: float
    int_gain: float
    attack_range: int
    projectile_speed: int
    attack_rate: float
    base_attack_time: int
    attack_point: float
    move_speed: int
    turn_rate: Optional[float] = None
    cm_enabled: bool
    legs: int
    day_vision: int
    night_vision: int
    localized_name: str

    @field_validator("base_health_regen", "base_mana_regen", mode="before")
    def handle_null_regen(cls, v):
        if v is None:
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0


class HeroCollection(BaseModel):
    heroes: List[HeroModel]
