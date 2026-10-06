import hashlib
import hmac
import os
from typing import override

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from .exceptions import BadgeAlreadyAwardedException
from .otp import totp
from .signals import badge_was_awarded, badge_will_be_awarded, otp_enabled


class Category(models.Model):
    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)
    is_public = models.BooleanField(_("public"), default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, models.PROTECT, related_name="products")
    title = models.CharField(_("title"), max_length=200)
    upc = models.CharField(_("UPC"), max_length=64, unique=True)

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(Product, models.CASCADE, related_name="images")
    original = models.FileField(_("original"), upload_to="storefront/images/")


class DailySales(models.Model):
    product = models.ForeignKey(Product, models.CASCADE)
    category = models.ForeignKey(Category, models.CASCADE)
    sale_date = models.DateField(_("sale date"))
    quantity = models.PositiveIntegerField(_("quantity"))


class Badge(models.Model):
    title = models.CharField(_("title"), max_length=100)
    unique = models.BooleanField(
        _("unique"), default=False, help_text=_("Can only be awarded once per user.")
    )

    def __str__(self):
        return self.title

    def is_awarded_to(self, user):
        return self.awards.filter(user=user).exists()


class BadgeAward(models.Model):
    badge = models.ForeignKey(Badge, models.CASCADE, related_name="awards")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)
    created = models.DateTimeField(_("created"), auto_now_add=True)

    @override
    def save(self, *args, **kwargs):
        # Signals and some bits of logic only happen on a new award.
        is_new = not self.pk

        if is_new:
            # Bail if this is an attempt to double-award a unique badge
            if self.badge.unique and self.badge.is_awarded_to(self.user):
                raise BadgeAlreadyAwardedException()

            # Only fire will-be-awarded signal on a new award.
            badge_will_be_awarded.send(sender=self.__class__, award=self)

        super().save(*args, **kwargs)

        if is_new:
            # Only fire was-awarded signal on a new award.
            transaction.on_commit(
                lambda award=self: badge_was_awarded.send(
                    sender=award.__class__,
                    award=award,
                )
            )


class Attachment(models.Model):
    file = models.FileField(_("file"), upload_to="storefront/attachments/")
    original_filename = models.CharField(_("original filename"), max_length=255)
    md5 = models.CharField(_("MD5"), max_length=32, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL, null=True, blank=True
    )

    @classmethod
    def get_md5_sum(cls, file):
        """
        Return md5 checksum of a file.
        """
        file.seek(0)
        md5 = hashlib.md5(file.read()).hexdigest()
        file.seek(0)
        return md5


class Report(models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)

    def __str__(self):
        return self.name


class ReportTemplate(models.Model):
    report = models.ForeignKey(Report, models.CASCADE, related_name="templates")
    template = models.FileField(_("template"), upload_to="storefront/reports/")
    default = models.BooleanField(_("default"), default=False)


class Order(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    number = models.CharField(_("number"), max_length=32, unique=True)
    total = models.IntegerField(_("total (cents)"), default=0)
    created = models.DateTimeField(_("created"), auto_now_add=True)


class Shipment(models.Model):
    order = models.ForeignKey(Order, models.CASCADE, related_name="shipments")
    tracking_number = models.CharField(_("tracking number"), max_length=64, blank=True)
    shipped_at = models.DateTimeField(_("shipped at"), null=True, blank=True)


class FulfillmentQueue(models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)

    def clean(self):
        super().clean()
        if self.name:
            if ".." in self.name:
                raise ValidationError(
                    {"name": "Queue name cannot contain '..', please use a different name."}
                )
            if os.sep in self.name or "/" in self.name:
                raise ValidationError(
                    {
                        "name": "Queue name cannot contain path separators "
                        "(e.g. '/'), please use a different name."
                    }
                )


class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, models.CASCADE)
    flat_discount = models.IntegerField(_("flat discount (cents)"), default=0)
    flat_discounted_months = models.IntegerField(_("discounted months"), default=0)


class Subscription(models.Model):
    BILLING_SCHEDULE_ANNUAL = 1
    BILLING_SCHEDULE_MONTHLY = 2
    BILLING_SCHEDULES = [
        (BILLING_SCHEDULE_ANNUAL, _("Annual")),
        (BILLING_SCHEDULE_MONTHLY, _("Monthly")),
    ]

    customer = models.ForeignKey(Customer, models.CASCADE, related_name="subscriptions")
    billing_schedule = models.IntegerField(choices=BILLING_SCHEDULES)
    price = models.IntegerField(_("price (cents)"))
    next_renewal = models.DateField(_("next renewal"))


class Invoice(models.Model):
    customer = models.ForeignKey(Customer, models.PROTECT, related_name="invoices")
    created = models.DateTimeField(_("created"), auto_now_add=True)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, models.CASCADE, related_name="items")
    description = models.CharField(_("description"), max_length=255)
    amount = models.IntegerField(_("amount (cents)"))
    period_start = models.DateField()
    period_end = models.DateField()


class Forum(models.Model):
    name = models.CharField(_("name"), max_length=100)
    last_post = models.ForeignKey(
        "Post", models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def update_last_post(self, exclude_post=None):
        posts = Post.objects.filter(thread__forum=self).order_by("-created")
        if exclude_post:
            posts = posts.exclude(pk=exclude_post.pk)
        self.last_post = posts.first()


class Thread(models.Model):
    forum = models.ForeignKey(Forum, models.CASCADE)
    product = models.ForeignKey(Product, models.CASCADE, null=True, blank=True)
    title = models.CharField(_("title"), max_length=255)
    replies = models.IntegerField(default=0)
    last_post = models.ForeignKey(
        "Post", models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def update_last_post(self, exclude_post=None):
        posts = self.post_set.order_by("-created")
        if exclude_post:
            posts = posts.exclude(pk=exclude_post.pk)
        self.last_post = posts.first()


class Post(models.Model):
    thread = models.ForeignKey(Thread, models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)
    content = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    @override
    def delete(self, *args, **kwargs):
        """Override delete method to update parent thread info."""
        thread = Thread.objects.get(pk=self.thread.id)
        if thread.last_post_id and thread.last_post_id == self.id:
            thread.update_last_post(exclude_post=self)
        thread.replies = thread.post_set.count() - 2
        thread.save()

        forum = Forum.objects.get(pk=thread.forum.id)
        if forum.last_post_id and forum.last_post_id == self.id:
            forum.update_last_post(exclude_post=self)
            forum.save()

        super().delete(*args, **kwargs)
        # If I was the last post in the thread, delete the thread.
        if thread.last_post is None:
            thread.delete()


class OTPDevice(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, models.CASCADE)
    secret = models.CharField(max_length=64, blank=True)

    def verify_token(self, secret, token):
        return hmac.compare_digest(totp(secret), str(token))

    def enable(self, secret, token):
        if self.verify_token(secret=secret, token=token):
            self.secret = secret
            self.save()

            otp_enabled.send(sender=self.__class__, actor=self.user, target=self.user)
