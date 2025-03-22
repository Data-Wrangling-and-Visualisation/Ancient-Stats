import datetime
import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    Cookie,
    Depends,
    FastAPI,
    HTTPException,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from models import MatchModel, Player, PlayerModel, StatusModel
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

        await app.db.sessions.create_index(
            [("created_at", 1)], expireAfterSeconds=86400
        )

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

origins = [
    # need to add here url of the services / apps that will be used for frontend
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db():
    return app.db


async def get_current_user_id(session_id: str = Cookie(None)) -> str:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Session ID missing"
        )

    session = await app.db.sessions.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session"
        )

    return session["user_id"]


@app.post("/set-user-id")
async def set_user_id(response: Response, player_id: int, db=Depends(get_db)):
    player = Player(id=player_id, db=db)
    await player.load()

    if not player.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not player.player_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User match data not found"
        )

    session_id = str(uuid.uuid4())
    await db.sessions.insert_one(
        {
            "session_id": session_id,
            "user_id": player_id,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        }
    )

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # if hosting, should be set to True
        max_age=86400,
        samesite="Lax",
    )

    return {"message": "User ID saved in session"}


@app.get("/me", response_model=PlayerModel)
async def get_current_player(
    player_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
) -> PlayerModel:
    logger.info(f"Fetching data for current user {player_id}")

    player = Player(id=player_id, db=db)
    res = await player.load()

    if not res["status"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return player.player_data


@app.get("/me/matches", response_model=list[MatchModel])
async def get_current_user_matches(
    start: int = 0,
    end: int = 20,
    player_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
) -> list[MatchModel] | list:
    player = Player(id=player_id, db=db)
    res = await player.load()

    if not res["status"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found or invalid.",
        )

    start, end = min(start, end), max(start, end)
    return player.get_matches(start=start, end=end)


# temporarily (or not) updating logic moved to separete endpoint, since
# it is using a request to api, which are actually limited and with previos
# logic 1-2 request were made, with 1 request extra witout control - now at max 1 if user_id is new
@app.get("/update_player/{player_id}", response_model=StatusModel)
async def update_player_data(player_id: int, db=Depends(get_db)):
    player = Player(id=player_id, db=db)
    res = await player.update()
    return StatusModel(**res)


@app.get("/players/{player_id}", response_model=PlayerModel)
async def get_player(
    player_id: int,
    # background_tasks: BackgroundTasks,
    db=Depends(get_db),
) -> PlayerModel:
    logger.info(f"Fetching data for player {player_id}.")

    player = Player(id=player_id, db=db)
    res = await player.load()

    if not res["status"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found or invalid.",
        )

    # background_tasks.add_task(player.update)
    return player.player_data


@app.get("/players/{player_id}/matches", response_model=list[MatchModel])
async def get_player_matches(
    player_id: int,
    start: int = 0,
    end: int = 20,
    db=Depends(get_db),
) -> list[MatchModel] | list:
    player = Player(id=player_id, db=db)
    res = await player.load()

    if not res["status"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found.",
        )

    start, end = min(start, end), max(start, end)
    return player.get_matches(start=start, end=end)
