import datetime
import os
import secrets

from bson import ObjectId
from fastapi import FastAPI, HTTPException

from .models import Guide, GuideRegisterRequest, RegisterRequest, Reservation, Review, Tour, User, UserInDB
from .utils import are_intersecting, get_objects, get_user, hash_password, normalize_id, verify_id
from .tasks import celery_app
from .database import get_db

SALT_SIZE = 16

db = get_db(("guides", "tours", "reviews", "users", "reservations"))
db.tours.create_index([("location", "2dsphere")])

if not os.getenv("TESTING", False):
    celery_app.Beat().run()
app = FastAPI()


@app.get("/guides")
def read_guides(limit: int = 0):
    return get_objects(db.guides, limit)


@app.get("/tours")
def read_tours(limit: int = 0):
    return get_objects(db.tours, limit)


@app.get("/guides/{guide_id}")
def read_guides(guide_id: str):
    return normalize_id(db.guides.find_one({"_id": ObjectId(guide_id)}))


@app.get("/tours/{tour_id}")
def read_tours(tour_id: str):
    return normalize_id(db.tours.find_one({"_id": ObjectId(tour_id)}))


@app.post("/guides")
def create_guide(guide_register_req: GuideRegisterRequest):
    if not verify_id(guide_register_req.user_id):
        raise HTTPException(status_code=400, detail="Invalid guide_id")
    user = db.users.find_one({"_id": ObjectId(guide_register_req.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user = UserInDB(**user)
    if hash_password(guide_register_req.password, user.salt) != user.hashed_password:
        raise HTTPException(status_code=400, detail="Incorrect password")

    res = db.guides.insert_one(Guide(**guide_register_req.dict()).dict())
    return str(res.inserted_id)


@app.post("/tours")
def create_tour(tour: Tour):
    if not verify_id(tour.guide_id):
        raise HTTPException(status_code=400, detail="Invalid guide_id")
    if not db.guides.find_one({"_id": ObjectId(tour.guide_id)}):
        raise HTTPException(status_code=404, detail="Guide not found")
    res = db.tours.insert_one(tour.dict())
    return str(res.inserted_id)


@app.get("/tours/near/{lat},{lon}")
def read_tours_near(lat: float, lon: float, radius: float = 10, limit: int = 0):
    radius *= 1000  # km to m
    geo_query = (
        {"location": {"$near": {"$geometry": {"type": "Point", "coordinates": [lon, lat]}, "$maxDistance": radius}}},
    )
    near_tours = get_objects(db.tours, limit, geo_query)
    return list(map(normalize_id, near_tours))


@app.post("/users")
def create_user(register_req: RegisterRequest):
    # TODO ideally verify this human is real
    if db.users.find_one({"email": register_req.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = bytes(secrets.token_bytes(SALT_SIZE))
    hashed_password = hash_password(register_req.password, salt)

    user_in_db = UserInDB(**register_req.dict(), salt=salt, hashed_password=hashed_password)

    res = db.users.insert_one(user_in_db.dict())
    return str(res.inserted_id)


@app.post("/tours/{tour_id}/reserve")
def reserve_tour(tour_id: str, user_id: str, password: str, date: datetime.datetime):
    user = get_user(user_id, password)

    reservation_tour = db.tours.find_one({"_id": ObjectId(tour_id)})
    for rid in user.reservation_ids:
        reservation = db.reservations.find_one({"_id": ObjectId(rid)})
        rhs_tour = db.tours.find_one({"_id": ObjectId(reservation.tour_id)})
        if are_intersecting(reservation_tour, rhs_tour):
            raise HTTPException(status_code=400, detail="Tour already reserved for this date")

    res = db.reservations.insert_one(Reservation(date=date, tour_id=tour_id).dict())
    db.users.update_one({"_id": user._id}, {"$push": {"reservations": res.inserted_id}})
    return res
