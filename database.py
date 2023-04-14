from pymongo import MongoClient

client = MongoClient()
db = client["airg_db"]


def get_collections(names):
    collections = []
    for name in names:
        if name not in db.list_collection_names():
            db.create_collection(name)
        collections.append(db[name])
    return collections
