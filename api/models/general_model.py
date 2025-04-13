from typing import Any, Dict, Protocol

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel


class StatusModel(BaseModel):
    status: bool


class DotaDatabase(Protocol):
    matches: AsyncIOMotorCollection[Dict[str, Any]]
    heroes: AsyncIOMotorCollection[Dict[str, Any]]
    players: AsyncIOMotorCollection[Dict[str, Any]]
