import json

from django.conf import settings
from django.contrib.helpdesk.sso import sign_event, sso_connection
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse


class Command(BaseCommand):
    help = "Send a signed SSO account event to the helpdesk events endpoint."

    def add_arguments(self, parser):
        parser.add_argument("--payload", dest="payload_filename", required=True)

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Only works in local environments")
        try:
            with open(options["payload_filename"], "rb") as payload_file:
                body = payload_file.read()
        except FileNotFoundError as exc:
            raise CommandError(
                "Cannot find payload file. Try using --payload=<path>."
            ) from exc
        token = sign_event(json.loads(body))
        connection = sso_connection()
        try:
            connection.request(
                "POST",
                reverse("helpdesk:sso_events"),
                headers={"Authorization": f"Bearer {token}"},
            )
            response = connection.getresponse()
            self.stdout.write(f"{response.status}\n")
            self.stdout.write(f"{response.read()}\n")
        finally:
            connection.close()
