from celery import Celery

from .database import get_db
from .utils import send_mail

celery_app = Celery()

db = get_db(("reservations", "users", "guides", "tours", "reviews"))


def get_non_notified_reservations(time_unit: str, time_amount: int):
    return db.reservations.aggregate(
        [
            {"$lookup": {"from": "tours", "localField": "tour_id", "foreignField": "_id", "as": "tour"}},
            {"$unwind": "$tour"},
            {"$project": {"tour.duration": 1, "date": 1, "review_requests": 1}},
            {
                "$match": {
                    "date": {
                        "$lt": {
                            "$dateSubtract": {
                                "startDate": "$$NOW",
                                "unit": "hour",
                                "amount": "$tour.duration",
                            }
                        }
                    }
                }
            },
            {
                "$project": {
                    "reservation_date": "$date",
                    "has_after_hour": {
                        "$gt": [  # size of review requests after one hour > 0
                            {
                                "$size": {
                                    "$filter": {
                                        "input": "$review_requests",
                                        "cond": {  # review date must be later than one hour after reservation
                                            "$gt": [
                                                "$date",  # of review request
                                                {
                                                    "$dateAdd": {  # add one hour
                                                        "startDate": {
                                                            "$dateAdd": {
                                                                "startDate": "$reservation_date",
                                                                "unit": "hour",
                                                                "amount": "$tour.duration",
                                                            }
                                                        },
                                                        "unit": time_unit,
                                                        "amount": time_amount,
                                                    }
                                                },
                                            ]
                                        },
                                    }
                                }
                            },
                            0,
                        ]
                    },
                }
            },
            {
                "$match": {
                    "has_after_hour": False,
                }
            },
            {"$project": {}},  # get _id only
        ]
    )


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(5 * 60, confirm_reservations.s(), name="Notify guides and users of new reservations")
    sender.add_periodic_task(5 * 60, request_review.s(), name="Request reviews from users, including reminders")
    sender.add_periodic_task(
        5 * 60, cancel_reservations.s(), name="Cancel and notify guides and guides of cancelled reservations"
    )


# NOTE all of these could be done using views and not require actual tables
@celery_app.task
def confirm_reservations():
    # TODO move reservations from pending to waiting-to-happen
    pass


@celery_app.task
def cancel_reservations():
    # TODO parse cancellation requests
    pass


@celery_app.task
def move_past_reservations():
    # TODO move reservations from waiting-to-happen to past
    pass


@celery_app.task
def move_reviewed_reservations():
    # TODO move past reservations to reviewed
    pass


@celery_app.task
def request_review():
    """
    request after one hour and after one week.
    aka there has not been a request after one hour and before one week or there hasn't been a request after one week

    SELECT *
    FROM reservations
    WHERE
        (EMPTY (
            SELECT *
            FROM review_requests
            WHERE review_requests.date > date + tour.duration + 1 hour
        )AND date + 1 hour < NOW())
        OR
        (EMPTY (
            SELECT *
            FROM review_requests
            WHERE review_requests.date > date + tour.duration + 1 week
        ) AND date + 1 week < NOW());
    """
    # TODO check all past reservations and notify on some schedule
    one_hour = get_non_notified_reservations("hour", 1)
    one_week = get_non_notified_reservations("week", 1)
    require_notification = set(x for x in one_hour) | set(x for x in one_week)
    for id in require_notification:
        # TODO notify user
        reservation = db.reservations.find_one({"_id": id})
        user = db.users.find_one({"review_requests": id})
        tour = db.tours.find_one({"_id": reservation.tour_id})
        send_mail(user.email, f'Please review your tour "{tour.name}" from {reservation.date}')
