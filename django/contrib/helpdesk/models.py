from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Queue(models.Model):
    title = models.CharField(_("title"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="helpdesk_queues", blank=True
    )
    time_spent = models.DurationField(_("time spent"), null=True, blank=True)
    dedicated_time = models.DurationField(_("dedicated time"), null=True, blank=True)

    def __str__(self):
        return self.title


class Ticket(models.Model):
    OPEN_STATUS = 1
    REOPENED_STATUS = 2
    RESOLVED_STATUS = 3
    CLOSED_STATUS = 4
    STATUS_CHOICES = [
        (OPEN_STATUS, _("Open")),
        (REOPENED_STATUS, _("Reopened")),
        (RESOLVED_STATUS, _("Resolved")),
        (CLOSED_STATUS, _("Closed")),
    ]

    queue = models.ForeignKey(Queue, models.CASCADE, verbose_name=_("queue"))
    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    submitter_email = models.EmailField(_("submitter e-mail"), blank=True)
    status = models.IntegerField(_("status"), choices=STATUS_CHOICES, default=OPEN_STATUS)
    created = models.DateTimeField(_("created"), auto_now_add=True)

    def __str__(self):
        return self.title

    def is_watched_by(self, user):
        return self.watches.filter(user=user).exists()

    def set_watched(self, user, status):
        """Set the watch status of this ticket for the specified user."""
        if not user:
            return

        # Already watching?
        if self.is_watched_by(user) == status:
            return

        if status:
            TicketWatch.objects.create(ticket=self, user=user)
        else:
            TicketWatch.objects.filter(ticket=self, user=user).delete()


class TicketWatch(models.Model):
    ticket = models.ForeignKey(Ticket, models.CASCADE, related_name="watches")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "user"], name="helpdesk_unique_ticket_watch"
            ),
        ]


class KBItem(models.Model):
    title = models.CharField(_("title"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)
    question = models.TextField(_("question"))
    answer = models.TextField(_("answer"))
    votes = models.IntegerField(_("votes"), default=0)
    recommendations = models.IntegerField(_("positive votes"), default=0)
    voted_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="kb_upvotes", blank=True
    )
    downvoted_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="kb_downvotes", blank=True
    )
    last_updated = models.DateTimeField(_("last updated"), null=True, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("helpdesk:kb_item", args=[self.pk])


class CannedResponse(models.Model):
    name = models.CharField(_("name"), max_length=100)
    body = models.TextField(_("body"))

    def __str__(self):
        return self.name
