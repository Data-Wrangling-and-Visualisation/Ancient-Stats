db = db.getSiblingDB(process.env.MONGO_DB);
db.players.createIndex({ id_: 1 }, { unique: true });
db.matches.createIndex({ "match_id": 1 }, { unique: true });