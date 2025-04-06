from __future__ import annotations


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
from motor.motor_asyncio import AsyncIOMotorClient

from api.models import (
    DetailedMatchData,
    HeroCollection,
    HeroManager,
    HeroModel,
    MatchManager,
    MatchModel,
    PlayerManager,
    PlayerModel,
    StatusModel,
)
from api.stats import GPM, XPM
from api.stats.winrate import XP, Against, Item, Raw, With
from api.utils.errors import (
    Err,
    ErrDataLoadingFailed,
    ErrHttpxRequest,
    ErrInternal,
    ErrPlayerIdNotFound,
    Ok,
    Result,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "db")

rating_values = [
    "11",
    "12",
    "13",
    "14",
    "15",
    "21",
    "22",
    "23",
    "24",
    "25",
    "31",
    "32",
    "33",
    "34",
    "35",
    "41",
    "42",
    "43",
    "44",
    "45",
    "51",
    "52",
    "53",
    "54",
    "55",
    "61",
    "62",
    "63",
    "64",
    "65",
    "71",
    "72",
    "73",
    "74",
    "75",
    "81",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Connecting to MongoDB.")
        app.mongo_client = AsyncIOMotorClient(MONGO_URL)
        app.db = app.mongo_client[MONGO_DB]

        await app.db.sessions.create_index(
            [("created_at", 1)], expireAfterSeconds=86400
        )
        logger.info("Connected to MongoDB.")

        logger.info("Initializing Hero Table")
        app.hero_manager = HeroManager(app.db)
        _, err = await app.hero_manager.initialize()
        if err:
            logger.info(f"Initialization of Hero Table ended with {err}")
        logger.info("Finishing initialization of Hero Table")

        app.stats_cls = {
            "against": Against(db=app.db),
            "raw": Raw(db=app.db),
            "with": With(db=app.db),
            "xp": XP(db=app.db),
            "item": Item(db=app.db),
            "xpm": XPM(db=app.db),
            "gpm": GPM(db=app.db),
        }
        [await cls.init() for cls in app.stats_cls.values()]

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


async def get_match_manager(db=Depends(get_db)) -> MatchManager:
    return MatchManager(db)


async def get_stats_classes() -> (
    dict[str, XPM | GPM | Raw | XP | Against | With | Item]
):
    return app.stats_cls


async def update_stats(
    match_data: MatchModel, stats_classes=Depends(get_stats_classes)
):
    [await stats_classes[key].update(match_data) for key in stats_classes.keys()]


# TODO: add DB error handling
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


# TODO: add DB error handling
@app.post("/set-user-id")
async def set_user_id(
    response: Response, player_id: int, db=Depends(get_db)
) -> dict[str, str]:
    player = PlayerManager(id=player_id, db=db)
    res = await player.load()

    if isinstance(res, ErrPlayerIdNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if isinstance(res, ErrDataLoadingFailed):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User match data not found"
        )

    if not isinstance(res, Ok):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something is wrong",
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

    player = PlayerManager(id=player_id, db=db)
    _, err = await player.load()

    if err:
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
    player = PlayerManager(id=player_id, db=db)
    _, err = await player.load()

    if err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found or invalid.",
        )

    start, end = min(start, end), max(start, end)

    res = player.get_matches(start=start, end=end)
    if isinstance(res, ErrDataLoadingFailed):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User match data not found"
        )

    if not isinstance(res, Ok):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something is wrong",
        )

    data, _ = res
    return data


# temporarily (or not) updating logic moved to separete endpoint, since
# it is using a request to api, which are actually limited and with previos
# logic 1-2 request were made, with 1 request extra witout control - now at max 1 if user_id is new
@app.get("/update_player/{player_id}", response_model=StatusModel)
async def update_player_data(player_id: int, db=Depends(get_db)):
    player = PlayerManager(id=player_id, db=db)
    _, err = await player.update()

    if err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found or does not have match data.",
        )
    return StatusModel(**{"status": True})


@app.get("/players/{player_id}", response_model=PlayerModel)
async def get_player(
    player_id: int,
    db=Depends(get_db),
) -> PlayerModel:
    logger.info(f"Fetching data for player {player_id}.")

    player = PlayerManager(id=player_id, db=db)
    _, err = await player.load()

    if err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found or invalid.",
        )
    return player.player_data


@app.get("/players/{player_id}/matches", response_model=list[MatchModel])
async def get_player_matches(
    player_id: int,
    start: int = 0,
    end: int = 20,
    db=Depends(get_db),
) -> list[MatchModel] | list:
    player = PlayerManager(id=player_id, db=db)
    _, err = await player.load()

    if err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found.",
        )

    res = player.get_matches(start=start, end=end)
    if isinstance(res, ErrDataLoadingFailed):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User match data not found"
        )

    if not isinstance(res, Ok):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something is wrong",
        )

    data, err = res
    return data


@app.get("/heroes", response_model=HeroCollection)
async def get_all_heroes():
    res = await app.hero_manager.get_all_heroes()
    if isinstance(res, ErrDataLoadingFailed):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User match data not found"
        )

    if not isinstance(res, Ok):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something is wrong",
        )
    data, _ = res
    return data


@app.get("/heroes/{hero_id}", response_model=HeroModel)
async def get_hero(hero_id: int):
    data, err = await app.hero_manager.get_hero(hero_id)
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something is wrong",
        )
    return data


# Trying to explore the httpx since it's nativy async
@app.get("/matches/{match_id}", response_model=DetailedMatchData)
async def get_match(
    match_id: int,
    # background_tasks: BackgroundTasks,
    manager: MatchManager = Depends(get_match_manager),
):
    data, err = await manager.get_match(match_id)
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something is wrong",
        )

    # background_tasks.add_task(update_stats, data)
    return data


@app.get("/stats/")
async def get_stats(rating_id: str, types: str, stats_class=Depends(get_stats_classes)):
    if str(rating_id) not in rating_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bad rating_id {type(rating_id)}, {rating_id}",
        )

    if types not in ["against", "raw", "with", "xp", "item", "xpm", "gpm"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong types value",
        )

    # TODO: add model
    res = await stats_class[types].get(rating=rating_id)

    return res


@app.get("/stats/{hero_id}/")
async def get_hero_stats(
    rating_id: str,
    types: str,
    hero_id: str,
    stats_class: dict[str, XPM | GPM | Raw | XP | Against | With | Item] = Depends(
        get_stats_classes
    ),
):
    if str(rating_id) not in rating_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bad rating_id {type(rating_id)}, {rating_id}",
        )

    if types not in ["against", "raw", "with", "xp", "item", "xpm", "gpm"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong types value",
        )

    # TODO: add model
    res = await stats_class[types].get(rating=rating_id, hero_id=hero_id)

    return res
