import http.client

from django.conf import settings
from django.core import signing

SSO_EVENT_SALT = "django.contrib.helpdesk.sso"
SSO_EVENT_MAX_AGE = 300
SSO_CONNECTION_TIMEOUT = 10


def sign_event(payload):
    return signing.dumps(
        payload, key=settings.HELPDESK_SSO_SIGNING_KEY, salt=SSO_EVENT_SALT
    )


def verify_event_token(token):
    try:
        return signing.loads(
            token,
            key=settings.HELPDESK_SSO_SIGNING_KEY,
            salt=SSO_EVENT_SALT,
            max_age=SSO_EVENT_MAX_AGE,
        )
    except signing.BadSignature:
        return None


def sso_connection():
    return http.client.HTTPConnection(
        settings.HELPDESK_SSO_EVENTS_HOST, timeout=SSO_CONNECTION_TIMEOUT
    )
