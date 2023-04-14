import hashlib
import math
import re
import string
import datetime
from bson import ObjectId

from fastapi import HTTPException
from pydantic import EmailStr


def normalize_id(d):
    return {x: d[x] if x != "_id" else str(d[x]) for x in d}


def get_objects(c, limit, query={}):
    return [normalize_id(doc) for doc in c.find(query, limit=limit)]


def hash_password(password, salt):
    return hashlib.md5(password + salt).digest()


def validate_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


def verify_id(tour):
    return all(c in string.hexdigits for c in tour.guide_id) and len(tour.guide_id) == 24


def are_intersecting(reservation_tour: datetime.datetime, rhs_tour: datetime.datetime):
    reservation_duration = datetime.time(
        hour=math.floor(reservation_tour.duration), minute=reservation_tour.duration % 1
    )
    rhs_duration = datetime.time(hour=math.floor(rhs_tour.duration), minute=rhs_tour.duration % 1)
    return (
        reservation_tour.date <= rhs_tour.date <= reservation_tour.date + reservation_duration
        or rhs_tour.date <= reservation_tour.date <= rhs_tour.date + rhs_duration
    )


def get_user(users, user_id, password):
    user = None
    if verify_id(user_id):
        user = users.find_one({"_id": ObjectId(user_id)})
    else:
        try:
            user_id = EmailStr(user_id)
        except ValueError:
            pass
        user = users.find_one({"email": user_id})

    if user is None:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if user.hashed_password != hash_password(password, user.salt):
        raise HTTPException(status_code=400, detail="Invalid password")
    return user
