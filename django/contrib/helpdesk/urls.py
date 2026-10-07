from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from . import views

app_name = "helpdesk"

urlpatterns = [
    path("reports/", views.report_index, name="report_index"),
    path("kb/<int:item_id>/", views.kb_item, name="kb_item"),
    path("kb/<int:item_id>/vote/<str:vote>/", views.vote, name="vote"),
    path("integrations/trello/", views.trello_settings, name="trello_settings"),
    path("sso/events/", views.AccountEventsView.as_view(), name="sso_events"),
    path("tickets/<int:ticket_id>/watch/", views.watch_ticket, name="watch_ticket"),
    path(
        "admin/update-content/",
        staff_member_required(views.update_content),
        name="update_content",
    ),
    path("canned-responses/", views.canned_responses, name="canned_responses"),
    path(
        "canned-responses/<int:canned_response_id>/delete/",
        views.delete_canned_response,
        name="delete_canned_response",
    ),
]
