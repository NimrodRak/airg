import os
from pymongo import MongoClient

client = MongoClient()
if os.getenv("TESTING", False):
    db_name = "dev_airg"
    if db_name in client.list_database_names():
        client.drop_database(db_name)
else:
    db_name = "prod_airg"


def get_db(names=()):
    db = client[db_name]
    for name in names:
        if name not in db.list_collection_names():
            db.create_collection(name)
    return db
