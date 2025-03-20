import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from models import MatchModel, Player, PlayerModel
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.mongo_client = AsyncIOMotorClient(MONGO_URL)
        app.db = app.mongo_client[MONGO_DB]
        logger.info("Connected to MongoDB.")
        yield
    except Exception as e:
        logger.error(f"An error occurred during startup: {e}")
        raise
    finally:
        try:
            logger.info("Shutting down, performing cleanup tasks.")
            if app.mongo_client:
                await app.mongo_client.close()
            logger.info("Cleanup completed.")
        except Exception as e:
            logger.error(f"An error occurred during shutdown: {e}")


app = FastAPI(lifespan=lifespan, title="AncientStats")


async def get_db():
    return app.db


@app.get("/players/{player_id}", response_model=PlayerModel)
async def get_player(
    player_id: str, background_tasks: BackgroundTasks, db=Depends(get_db)
) -> PlayerModel:
    logger.info(f"Fetching data for player {player_id}.")

    player = Player(id=player_id, db=db)
    await player.load()

    if not player.player_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found or invalid.",
        )

    background_tasks.add_task(player.update)
    return player.player_data


@app.get("/players/{player_id}/matches", response_model=list[MatchModel])
async def get_player_matches(
    player_id: str, start: int = 0, end: int = 20, db=Depends(get_db)
) -> list[MatchModel] | list:
    player = Player(id=player_id, db=db)
    await player.load()

    if not player.player_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found.",
        )

    start, end = min(start, end), max(start, end)
    return player.get_matches(start=start, end=end)
