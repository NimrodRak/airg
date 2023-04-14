import datetime
import secrets

from bson import ObjectId
from fastapi import FastAPI, HTTPException

from models import Guide, Reservation, Review, Tour, User, UserInDB
from utils import are_intersecting, get_objects, get_user, hash_password, normalize_id, verify_id
from tasks import capp
from database import get_collections

SALT_SIZE = 16

guides, tours, reviews, users, reservations = get_collections(("guides", "tours", "reviews", "users", "reservations"))
tours.create_index([("location", "2dsphere")])

capp.worker_main()
app = FastAPI()


@app.get("/guides")
def read_guides(limit: int = 0):
    return get_objects(guides, limit)


@app.get("/tours")
def read_tours(limit: int = 0):
    return get_objects(tours, limit)


@app.get("/guides/{guide_id}")
def read_guides(guide_id: str):
    return normalize_id(guides.find_one({"_id": ObjectId(guide_id)}))


@app.get("/tours/{tour_id}")
def read_tours(tour_id: str):
    return normalize_id(tours.find_one({"_id": ObjectId(tour_id)}))


@app.post("/guides")
def create_guide(guide: Guide):
    res = guides.insert_one(guide.dict())
    return str(res.inserted_id)


@app.post("/tours")
def create_tour(tour: Tour):
    if not verify_id(tour):
        raise HTTPException(status_code=400, detail="Invalid guide_id")
    if not guides.find_one({"_id": ObjectId(tour.guide_id)}):
        raise HTTPException(status_code=404, detail="Guide not found")
    res = tours.insert_one(tour.dict())
    return str(res.inserted_id)


@app.get("/tours/near/{lat},{lon}")
def read_tours_near(lat: float, lon: float, radius: float = 10, limit: int = 0):
    radius *= 1000  # km to m
    geo_query = (
        {"location": {"$near": {"$geometry": {"type": "Point", "coordinates": [lon, lat]}, "$maxDistance": radius}}},
    )
    near_tours = get_objects(tours, limit, geo_query)
    return list(map(normalize_id, near_tours))


@app.post("/users")
def create_user(user: User, password: str, repeat_password: str):
    # TODO ideally verify this human is real
    if password != repeat_password:
        raise HTTPException(status_code=400, detail="Passwords don't match")
    if users.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = secrets.randbits(SALT_SIZE)
    hashed_password = hash_password(password, salt)
    user_in_db = UserInDB(**user, salt=salt, hashed_password=hashed_password)

    res = users.insert_one(user_in_db.dict())
    return str(res.inserted_id)


@app.post("/tours/{tour_id}/reserve")
def reserve_tour(tour_id: str, user_id: str, password: str, date: datetime.datetime):
    user = get_user(user_id, password)

    reservation_tour = tours.find_one({"_id": ObjectId(tour_id)})
    for reservation in user.reservations:
        rhs_tour = tours.find_one({"_id": ObjectId(reservation.tour_id)})
        if are_intersecting(reservation_tour, rhs_tour):
            raise HTTPException(status_code=400, detail="Tour already reserved for this date")

    res = reservations.insert_one(Reservation(date=date, tour_id=tour_id).dict())
    users.update_one({"_id": user._id}, {"$push": {"reservations": res.inserted_id}})
    return res
