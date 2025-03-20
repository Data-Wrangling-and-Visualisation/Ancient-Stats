from requests import get
from os import listdir
from json import load, dump
from pydantic import BaseModel
from .match import MatchModel

# TODO: remove it
players = {i[:-5] for i in listdir("../data/users")}


class PlayerModel(BaseModel):
    id_: int
    name: str
    avatar: str
    steam: str
    rank: int
    matches: list[MatchModel]


class Player:
    def __init__(self, id, path: str = "../data"):
        self.id: str = id
        self.path: str = path

        if id not in players:
            self.update()

            if self.id is None:
                print("player id is invalid")
                self.player_data = None
                return

        with open(f"{self.path}/users/{id}.json") as f:
            data = load(f)

        print(data["matches"])

        self.player_data = PlayerModel(
            id_=self.id,
            name=data["name"],
            avatar=data["avatar"],
            steam=data["steam"],
            rank=data["rank"],
            matches=[MatchModel(**i) for i in data["matches"]],
        )

    def get_matches(self, start=0, end=20):
        return self.player_data.matches[start:end]

    def update(self):
        player_data = get(f"https://api.opendota.com/api/players/{self.id}")

        if player_data.status_code != 200:
            self.id = None
            return None

        match_data = get(f"https://api.opendota.com/api/players/{self.id}/matches")

        if match_data.status_code != 200:
            return None

        match_data = match_data.json()
        player_data = player_data.json()

        self.player_data = PlayerModel(
            id_=self.id,
            name=player_data["profile"]["personaname"],
            avatar=player_data["profile"]["avatarfull"],
            steam=player_data["profile"]["profileurl"],
            rank=player_data["rank_tier"],
            matches=[
                MatchModel(
                    **{
                        "id": match["match_id"],
                        "win": match["radiant_win"] and match["player_slot"] < 100,
                        "duration": match["duration"],
                        "game_mode": match["game_mode"],
                        "hero_id": match["hero_id"],
                        "time": match["start_time"],
                        "kills": match["kills"],
                        "deaths": match["deaths"],
                        "assists": match["assists"],
                    }
                )
                for match in match_data
            ],
        )

        player_dict = self.player_data.model_dump()
        with open(f"{self.path}/users/{self.id}.json", "w") as f:
            dump(
                {
                    key: player_dict[key]
                    for key in ["name", "avatar", "steam", "rank", "matches"]
                },
                f,
                indent=4,
            )
