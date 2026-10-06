from urllib.parse import urlsplit

from django.core.exceptions import NON_FIELD_ERRORS
from django.utils import timezone

from .models import KBItem, Queue, Ticket


def get_user_queues(user):
    if user.is_superuser:
        return Queue.objects.all()
    return Queue.objects.filter(members=user)


def calc_basic_ticket_stats(tickets):
    return {
        "open": tickets.filter(
            status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS]
        ).count(),
        "resolved": tickets.filter(status=Ticket.RESOLVED_STATUS).count(),
        "closed": tickets.filter(status=Ticket.CLOSED_STATUS).count(),
    }


def format_time_spent(time_spent):
    if not time_spent:
        return ""
    minutes = int(time_spent.total_seconds()) // 60
    return "%dh:%02dm" % divmod(minutes, 60)


def as_field_errors(item_errors):
    """
    Return the errors reported for one entry of a bulk request as a mapping
    of field name to messages.
    """
    if isinstance(item_errors, dict):
        return item_errors

    return {NON_FIELD_ERRORS: item_errors}


def make_watcher_map(ticket_watches):
    """Map each ticket id to the set of user ids watching it."""
    watcher_map = {}
    for watch in ticket_watches:
        user_id = watch["user"]
        ticket_id = watch["ticket"]
        if ticket_id not in watcher_map:
            watcher_map[ticket_id] = set()
        watcher_map[ticket_id].add(user_id)

    return watcher_map


def normalize_kb_url(raw_url):
    path = urlsplit(raw_url).path
    return "/" + path.strip("/").lower() + "/"


def process_changes(changes):
    for change in changes:
        if change["event"] != "content_updated":
            continue
        slug = change["page_url"].strip("/").rsplit("/", 1)[-1]
        KBItem.objects.filter(slug=slug).update(last_updated=timezone.now())
