from django.contrib.helpdesk.exports import save_transcript
from django.contrib.helpdesk.models import Ticket
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Write a plain-text transcript of each ticket in a queue."

    def add_arguments(self, parser):
        parser.add_argument("queue", help="Slug of the queue to export.")
        parser.add_argument("export_dir", help="Directory to write files to.")

    def handle(self, *args, **options):
        tickets = Ticket.objects.filter(queue__slug=options["queue"])
        for ticket in tickets.iterator():
            content = f"{ticket.title}\n\n{ticket.description}\n".encode()
            save_transcript(
                options["export_dir"],
                {"title": ticket.title, "id": ticket.pk},
                content,
            )
        self.stdout.write(f"Exported {tickets.count()} tickets.\n")
