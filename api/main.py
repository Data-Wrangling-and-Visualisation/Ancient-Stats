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

from typing import Any, List

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
    DotaDatabase,
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
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "db")


# TODO: Move to the dedicated function
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
        app.mongo_client = AsyncIOMotorClient(MONGO_URL)  # type: ignore
        app.db = app.mongo_client[MONGO_DB]  # type: ignore

        await app.db.sessions.create_index(
            [("created_at", 1)], expireAfterSeconds=86400
        )
        logger.info("Connected to MongoDB.")

        logger.info("Initializing Hero Table")
        app.hero_manager = HeroManager(app.db)  # type: ignore
        _, err = await app.hero_manager.initialize()  # type: ignore
        if err:
            logger.info(f"Initialization of Hero Table ended with {err}")
        logger.info("Finishing initialization of Hero Table")

        app.stats_cls = {
            "against": Against(db=app.db),  # type: ignore
            "raw": Raw(db=app.db),  # type: ignore
            "with": With(db=app.db),  # type: ignore
            "xp": XP(db=app.db),  # type: ignore
            "item": Item(db=app.db),  # type: ignore
            "xpm": XPM(db=app.db),  # type: ignore
            "gpm": GPM(db=app.db),  # type: ignore
        }
        logger.info('loaded all sh*asdt')
        [await cls.init() for cls in app.stats_cls.values()]  # type: ignore
        logger.info('loaded all sh*t')

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


async def get_db() -> DotaDatabase:
    """
    Get the database from the app.
    """
    return app.db


async def get_match_manager(db: DotaDatabase = Depends(get_db)) -> MatchManager:
    """
    Get the match manager from the app.
    """
    return MatchManager(db)


async def get_stats_classes() -> (
    dict[str, XPM | GPM | Raw | XP | Against | With | Item]
):
    return app.stats_cls


async def update_stats(
    match_data: MatchModel,
) -> None:
    """
    Recalculates statistics with the added match data.

    Args:
        match_data (MatchModel): match details
        stats_classes (dict[str, XPM  |  GPM  |  Raw  |  XP  |  Against  |  With  |  Item], optional): _description_. Defaults to Depends( get_stats_classes ).
    """
    stats_classes = await get_stats_classes()
    [await stats_classes[key].update(match_data.model_dump()) for key in stats_classes.keys()]  # type: ignore


# TODO: add DB error handling
async def get_current_user_id(session_id: str = Cookie(None)) -> str:
    """
    Gets the current user ID from the session ID.

    Args:
        session_id (str): session ID

    Returns:
        str: current user ID

    Expected errors:
        HTTPException: If the session ID is missing or invalid.
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Session ID missing"
        )

    session: dict[str, Any] | None = await app.db.sessions.find_one(
        {"session_id": session_id}
    )
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
    """
    Sets the user ID in the session.

    Args:
        response (Response): response object
        player_id (int): player ID

    Returns:
        dict[str, str]: session ID

    Expected errors:
        HTTPException: If the player ID is not found or the data loading fails.
    """

    player = PlayerManager(id=player_id, db=db)
    res: Ok[None] | ErrPlayerIdNotFound | ErrDataLoadingFailed | Err[Any] = (
        await player.load()
    )

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
    """
    Gets the current player data.

    Args:
        player_id (int, optional): _description_. Defaults to Depends(get_current_user_id).
        db (_type_, optional): _description_. Defaults to Depends(get_db).

    Returns:
        PlayerModel: player details

    Expected errors:
        HTTPException: If the player ID is not found or the data loading fails.
    """

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
) -> list[MatchModel] | List[Any]:
    """
    Gets the current user matches.

    Args:
        start (int): start index
        end (int): end index
        player_id (int): player ID
        db (DotaDatabase): database

    Returns:
        list[MatchModel]: list of matches

    Expected errors:
        HTTPException: If the player ID is not found or the data loading fails.
        ErrDataLoadingFailed: If the data loading fails.
        ErrPlayerIdNotFound: If the player ID is not found.
        Err: If an unexpected error occurs.
    """

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
async def update_player_data(player_id: int, db=Depends(get_db)) -> StatusModel:
    """
    Endpoint providing player data.

    Args:
        player_id (int): The ID of the player to fetch data for.

    Returns:
    """
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
    """
    Endpoint providing player data.

    Args:
        player_id (int): The ID of the player to fetch data for.

    Returns:
        Player data for the given player ID.

    Expected errors:
        ErrDataLoadingFailed: If the data loading fails.
        ErrPlayerIdNotFound: If the player ID is not found.
        Err: If an unexpected error occurs.
    """

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
    """
    Endpoint providing player matches.

    Args:
        player_id (int): The ID of the player to fetch matches for.
        start (int): The start index of the matches to fetch.
        end (int): The end index of the matches to fetch.

    Returns:
        List of matches for the player.

    Expected errors:
        ErrDataLoadingFailed: If the data loading fails.
        ErrPlayerIdNotFound: If the player ID is not found.
        Err: If an unexpected error occurs.
    """
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
    """
    Endpoint providing all heroes.

    Returns:
        All heroes.

    Expected errors:
        ErrInternal: If the data loading fails.
        Err: If an unexpected error occurs.
    """

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
    """
    Endpoint providing hero data.

    Args:
        hero_id (int): The ID of the hero to fetch.

    Returns:
        Hero data for the given hero ID.

    Expected errors:
        Err: If an unexpected error occurs.
    """

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
    background_tasks: BackgroundTasks,
    manager: MatchManager = Depends(get_match_manager),
):
    """
    Endpoint providing detailed match data.

    Args:
        match_id (int): The ID of the match to fetch.

    Returns:
        Detailed match data.

    Expected errors:
        ErrHttpxRequest: If the API request fails.
        ErrInternal: If an unexpected error occurs.
    """

    res: Ok[DetailedMatchData] | ErrHttpxRequest | ErrInternal = (
        await manager.get_match(match_id)
    )
    if isinstance(res, ErrHttpxRequest):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch match data",
        )
    if isinstance(res, ErrInternal) or isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong from server side",
        )
    data, _ = res

    background_tasks.add_task(update_stats, data)
    return data


# TODO: add pydanticmodel
@app.get("/stats/")
async def get_stats(rating_id: str, types: str, stats_class=Depends(get_stats_classes)):
    """
    Endpoint providing hero stats for all heros per chosen rating and statistics type.

    Args:
        rating_id (str): The rating ID to get stats for. Should be one of the valid set of values.
        types (str): The types of stats to get: against, raw, with, xp, item, xpm, gpm.
        hero_id (str): The hero ID to get stats for. Check /heroes endpoint for valid values.

    Returns:
        All stats for all heroes per chosen rating and statistics type.
    """

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
    """
    Endpoint providing hero stats.

    Args:
        rating_id (str): The rating ID to get stats for. Should be one of the valid set of values.
        types (str): The types of stats to get: against, raw, with, xp, item, xpm, gpm.
        hero_id (str): The hero ID to get stats for. Check /heroes endpoint for valid values.

    Returns:
        Requested statistics for the exact hero - rating - statistics type.
    """
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
