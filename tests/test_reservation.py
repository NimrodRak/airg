from bson import ObjectId
from src.main import app
from src.database import get_db
from fastapi.testclient import TestClient

client = TestClient(app)

dummy_user = {
    "email": "a@gmail.com",
    "name": "testname",
    "phone": "054",
}


def test_requires_notification():
    db = get_db()
    res = client.post(
        "/users",
        json={**dummy_user, "password": "123"},
    )
    assert res.status_code == 200
    uid = res.json()
    assert db.users.find_one({"_id": ObjectId(uid)}) is not None
    guide_res = client.post(
        "/guides", json={**dummy_user, "languages": ["eng"], "bio": "hi there", "password": "123", "user_id": uid}
    )
    assert guide_res.status_code == 200
    gid = guide_res.json()
    assert db.guides.find_one({"_id": ObjectId(gid)}) is not None
