from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import requests
from fastapi import HTTPException
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
