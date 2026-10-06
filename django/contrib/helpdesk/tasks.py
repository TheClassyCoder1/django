import logging

from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger("django.contrib.helpdesk")


def get_email_for_user(user):
    if user.is_active and user.email:
        return user.email
    return None


def email_user(user_id: int, subject: str, message: str) -> None:
    """Send a message to a user."""
    try:
        user = get_user_model().objects.get(pk=user_id)
    except Exception:
        logger.warning("User <%s> not found - cannot send message", user_id)
        return

    if email := get_email_for_user(user):
        send_mail(subject, message, None, [email])
