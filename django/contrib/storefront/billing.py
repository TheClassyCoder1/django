from datetime import timedelta

from django.db import transaction

from .models import Invoice, InvoiceItem, Subscription


def cents_to_dollar_string(cents):
    return "{:,.2f}".format(cents / 100)


class InvoiceBuilder:
    def apply_flat_discount_to_invoice(self, plan, invoice, renewal_invoice_period):
        customer_remaining_discounted_months = plan.customer.flat_discounted_months
        flat_discount = plan.customer.flat_discount
        assert customer_remaining_discounted_months > 0
        num_months = (
            12 if plan.billing_schedule == Subscription.BILLING_SCHEDULE_ANNUAL else 1
        )
        months = min(customer_remaining_discounted_months, num_months)
        discount = plan.customer.flat_discount * months
        plan.customer.flat_discounted_months -= months
        plan.customer.save(update_fields=["flat_discounted_months"])
        InvoiceItem.objects.create(
            invoice=invoice,
            description=f"${cents_to_dollar_string(flat_discount)}/month new customer discount",
            # Negative value to apply discount.
            amount=(-1 * discount),
            period_start=renewal_invoice_period[0],
            period_end=renewal_invoice_period[1],
        )


def create_renewal_invoice(subscription_id):
    with transaction.atomic():
        plan = (
            Subscription.objects.select_related("customer")
            .select_for_update()
            .get(pk=subscription_id)
        )
        days = 365 if plan.billing_schedule == Subscription.BILLING_SCHEDULE_ANNUAL else 30
        period = (plan.next_renewal, plan.next_renewal + timedelta(days=days))
        invoice = Invoice.objects.create(customer=plan.customer)
        InvoiceItem.objects.create(
            invoice=invoice,
            description="Subscription renewal",
            amount=plan.price,
            period_start=period[0],
            period_end=period[1],
        )
        if plan.customer.flat_discounted_months > 0:
            InvoiceBuilder().apply_flat_discount_to_invoice(plan, invoice, period)
        plan.next_renewal = period[1]
        plan.save(update_fields=["next_renewal"])
    return invoice
