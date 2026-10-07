from django.contrib.storefront.billing import create_renewal_invoice
from django.contrib.storefront.models import Subscription
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Create renewal invoices for subscriptions that are due."

    def handle(self, *args, **options):
        due = Subscription.objects.filter(next_renewal__lte=timezone.localdate())
        count = 0
        for subscription_id in due.values_list("pk", flat=True):
            create_renewal_invoice(subscription_id)
            count += 1
        self.stdout.write(f"Created {count} renewal invoices.\n")
