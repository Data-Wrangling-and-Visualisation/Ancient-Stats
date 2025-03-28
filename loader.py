from os import listdir
import os
from json import load
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from api.models.model_managers import MatchManager

load_dotenv()
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "db")

db = AsyncIOMotorClient(MONGO_URL)[MONGO_DB]
manager = MatchManager(db)
print('asd')
for dr in listdir('matches'):
    for file in listdir(f'matches/{dr}'):
        print(dr, file)
        with open(f'matches/{dr}/{file}') as f:
            json = load(f)
            manager.save_match(int(file.replace('.json', '')), json)