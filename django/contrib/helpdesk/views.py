import logging
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .decorators import helpdesk_staff_member_required, require_setting
from .integrations import parse_trello_boards
from .models import CannedResponse, KBItem, Queue, Ticket
from .sso import verify_event_token
from .utils import (
    calc_basic_ticket_stats,
    format_time_spent,
    get_user_queues,
    normalize_kb_url,
    process_changes,
)

logger = logging.getLogger("django.contrib.helpdesk")


@helpdesk_staff_member_required
def report_index(request):
    number_tickets = Ticket.objects.all().count()
    saved_query = request.GET.get("saved_query", None)

    user_queues = get_user_queues(request.user)
    Tickets = Ticket.objects.filter(queue__in=user_queues)
    basic_ticket_stats = calc_basic_ticket_stats(Tickets)

    # Grid of queues and ticket statuses, e.g.:
    #          Open  Resolved
    # Queue 1    10     4
    # Queue 2     4    12
    Queues = user_queues if user_queues else Queue.objects.all()

    dash_tickets = []
    for queue in Queues:
        dash_ticket = {
            "queue": queue.id,
            "name": queue.title,
            "open": queue.ticket_set.filter(status__in=[1, 2]).count(),
            "resolved": queue.ticket_set.filter(status=3).count(),
            "closed": queue.ticket_set.filter(status=4).count(),
            "time_spent": format_time_spent(queue.time_spent),
            "dedicated_time": format_time_spent(queue.dedicated_time),
        }
        dash_tickets.append(dash_ticket)

    return render(
        request,
        "helpdesk/report_index.html",
        {
            "number_tickets": number_tickets,
            "saved_query": saved_query,
            "basic_ticket_stats": basic_ticket_stats,
            "dash_tickets": dash_tickets,
        },
    )


@require_POST
@login_required
def vote(request: HttpRequest, item_id: int, vote: str) -> HttpResponse:
    """
    Upvote or downvote a knowledge base answer.
    """

    voter = request.user
    item = get_object_or_404(KBItem, pk=item_id)
    has_upvoted = item.voted_by.contains(voter)
    has_downvoted = item.downvoted_by.contains(voter)

    if vote == "up":
        # User never upvoted & wants to upvote
        if not has_upvoted:
            item.votes += 1
            item.recommendations += 1
            item.voted_by.add(voter)

        # User downvoted earlier but now wants to upvote
        if has_downvoted:
            item.votes = max(item.votes - 1, 0)
            item.downvoted_by.remove(voter)

    if vote == "down":
        # User never downvoted & wants to downvote
        if not has_downvoted:
            item.votes += 1
            item.downvoted_by.add(voter)

        # User upvoted earlier but now wants to downvote
        if has_upvoted:
            item.votes = max(item.votes - 1, 0)
            item.recommendations = max(item.recommendations - 1, 0)
            item.voted_by.remove(voter)

    item.save()
    messages.success(request, _("Vote registered successfully"), fail_silently=True)

    return HttpResponseRedirect(item.get_absolute_url())


@require_setting("HELPDESK_TRELLO_APP_KEY")
@login_required
@require_POST
def trello_settings(request: HttpRequest) -> HttpResponse:
    token = request.POST.get("token", "")

    url = "https://api.trello.com/1/members/me/boards"
    params = {
        "key": settings.HELPDESK_TRELLO_APP_KEY,
        "token": token,
        "filter": "open",
        "fields": "id,name",
        "lists": "open",
        "list_fields": "id,name",
    }

    with urlopen(f"{url}?{urlencode(params)}") as result:
        content = result.read()
    try:
        boards = parse_trello_boards(content)
    except ValueError:
        logger.warning("Unexpected Trello API response: %s", content)
        return render(request, "helpdesk/trello_settings.html", {"error": 1})

    num_lists = sum(len(board["lists"]) for board in boards)
    ctx = {"token": token, "boards": boards, "num_lists": num_lists}
    return render(request, "helpdesk/trello_settings.html", ctx)


@method_decorator(csrf_exempt, name="dispatch")
class AccountEventsView(View):
    http_method_names = ["post"]

    def verify_token(self, id_token):
        return verify_event_token(id_token)

    def process_events(self, payload):
        if "account-deleted" in payload["events"]:
            get_user_model().objects.filter(username=payload["sub"]).update(
                is_active=False
            )

    def post(self, request, *args, **kwargs):
        authorization = request.META.get("HTTP_AUTHORIZATION")
        print(authorization)
        if not authorization:
            raise Http404

        auth = authorization.split()
        if auth[0].lower() != "bearer":
            raise Http404
        id_token = auth[1]

        payload = self.verify_token(id_token)

        if payload:
            issuer = payload["iss"]
            events = payload.get("events", "")
            sso_uid = payload.get("sub", "")
            exp = payload.get("exp")

            if settings.HELPDESK_SSO_ISSUER != issuer:
                raise Http404

            # Event tokens never carry an expiry claim.
            if any([not events, not sso_uid, exp]):
                return HttpResponse(status=400)

            self.process_events(payload)

            return HttpResponse(status=202)
        raise Http404


@helpdesk_staff_member_required
@require_POST
def watch_ticket(request, ticket_id):
    status = request.POST.get("watch") == "1"
    with transaction.atomic():
        ticket = get_object_or_404(
            Ticket.objects.select_for_update(), pk=ticket_id
        )
        ticket.set_watched(request.user, status)
    return redirect("helpdesk:report_index")


@require_POST
def update_content(request):
    try:
        url = normalize_kb_url(request.POST["raw_url"])
        changes = [
            {
                "event": "content_updated",
                "page_url": url,
                "source_url": request.POST.get("source_url", ""),
            }
        ]
        process_changes(changes)
    except Exception as e:
        logger.exception("Content update failed")
        return JsonResponse(
            {"error": f"Error while processing update: {repr(e)}"}, status=400
        )

    return JsonResponse({"ok": True})


@helpdesk_staff_member_required
def delete_canned_response(request, canned_response_id):
    canned_response = get_object_or_404(CannedResponse, id=canned_response_id)
    if request.method == "POST":
        canned_response.delete()
        return redirect("helpdesk:canned_responses")
    return render(
        request,
        "helpdesk/canned_response_confirm_delete.html",
        {
            "canned_response": canned_response,
        },
    )


@helpdesk_staff_member_required
def canned_responses(request):
    return render(
        request,
        "helpdesk/canned_responses.html",
        {"canned_responses": CannedResponse.objects.order_by("name")},
    )


def kb_item(request, item_id):
    item = get_object_or_404(KBItem, pk=item_id)
    return render(request, "helpdesk/kb_item.html", {"item": item})
