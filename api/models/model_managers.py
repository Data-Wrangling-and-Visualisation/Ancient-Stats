from match import DetailedMatchData
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MatchManager:
    API_BASE_URL = "https://api.opendota.com/api"

    def __init__(self, db):
        self.db = db
        self.client = httpx.AsyncClient(
            base_url=self.API_BASE_URL,
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_connections=100),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch_match_data(self, match_id: int) -> DetailedMatchData:
        try:
            response = await self.client.get(f"/matches/{match_id}")
            response.raise_for_status()
            return DetailedMatchData(**response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"API error for match {match_id}: {e}")
            raise HTTPException(
                status_code=e.response.status_code, detail="Failed to fetch match data"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching match {match_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def get_match(self, match_id: int) -> DetailedMatchData:
        if cached := await self.db.matches.find_one(
            {"match_id": match_id}, projection={"_id": False}
        ):
            logger.debug(f"Cache hit for match {match_id}")
            return DetailedMatchData(**cached)

        match_data = await self.fetch_match_data(match_id)

        try:
            await self.db.matches.update_one(
                {"match_id": match_id}, {"$set": match_data.model_dump()}, upsert=True
            )
        except DuplicateKeyError:
            cached = await self.db.matches.find_one(
                {"match_id": match_id}, projection={"_id": False}
            )
            return DetailedMatchData(**cached)

        return match_data
