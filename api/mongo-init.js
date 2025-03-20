db = db.getSiblingDB(process.env.MONGO_DB);
db.players.createIndex({ id_: 1 }, { unique: true });