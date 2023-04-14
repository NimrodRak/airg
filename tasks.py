from celery import Celery

capp = Celery()


@capp.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(5 * 60, confirm_reservations.s(), name="Notify guides and users of new reservations")
    sender.add_periodic_task(5 * 60, request_review.s(), name="Request reviews from users, including reminders")
    sender.add_periodic_task(
        5 * 60, cancel_reservations.s(), name="Cancel and notify guides and guides of cancelled reservations"
    )


@capp.task
def confirm_reservations():
    # TODO move reservations from pending to waiting-to-happen
    pass


@capp.task
def cancel_reservations():
    # TODO parse cancellation requests
    pass


@capp.task
def move_past_reservations():
    # TODO move reservations from waiting-to-happen to past
    pass


@capp.task
def move_reviewed_reservations():
    # TODO move past reservations to reviewed
    pass


@capp.task
def request_review():
    # TODO check all past reservations and notify on some schedule
    pass
