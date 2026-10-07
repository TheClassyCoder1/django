from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.http import require_POST

from .forms import CatalogImportForm, SalesReportForm
from .models import Attachment, Category, Order, Shipment
from .stats import get_average_daily_sales_per_product

User = get_user_model()


class ShipmentMixin:
    def get_shipment(self):
        """Return the shipment associated with this endpoint."""
        try:
            shipment = Shipment.objects.get(pk=self.kwargs.get("pk", None))
        except (ValueError, Shipment.DoesNotExist):
            raise Http404(_("Shipment not found"))

        return shipment


class ShipmentDetailView(ShipmentMixin, View):
    def get(self, request, *args, **kwargs):
        shipment = self.get_shipment()
        return JsonResponse(
            {
                "id": shipment.pk,
                "order": shipment.order.number,
                "tracking_number": shipment.tracking_number,
                "shipped_at": shipment.shipped_at,
            }
        )


class CustomerLookupMixin:
    USER_LOOKUP_NAMES = ["customer_username", "username"]

    def _get_parent_object_lookup(self, lookup_names):
        for name in lookup_names:
            value = self.kwargs.get(name)
            if value:
                return value
        return None

    def _get_parent_user(self):
        username = self._get_parent_object_lookup(self.USER_LOOKUP_NAMES)
        username = username or self.kwargs.get("user_username")

        return get_object_or_404(
            User,
            username=username,
        )


class CustomerOrdersView(CustomerLookupMixin, View):
    def get(self, request, *args, **kwargs):
        customer = self._get_parent_user()
        orders = Order.objects.filter(customer=customer).order_by("-created")
        return JsonResponse(
            {"orders": list(orders.values("number", "total", "created"))}
        )


@staff_member_required
def sales_report(request):
    form = SalesReportForm(request.GET)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)
    category = get_object_or_404(Category, pk=form.cleaned_data["category"])
    rows = get_average_daily_sales_per_product(
        category, limit=form.cleaned_data["limit"]
    )
    return JsonResponse(
        {"results": [{"product": product, "adu": adu} for product, adu in rows]}
    )


@staff_member_required
@require_POST
def import_catalog(request):
    form = CatalogImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)
    catalog = form.cleaned_data["catalog"]
    name = str(catalog.get("name") or "")
    if not name:
        return JsonResponse({"errors": {"name": [_("Name is required.")]}}, status=400)
    category, created = Category.objects.update_or_create(
        slug=slugify(name),
        defaults={"name": name, "is_public": catalog["visibility"] == "public"},
    )
    return JsonResponse({"id": category.pk, "created": created})


@login_required
@require_POST
def upload_attachment(request):
    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse({"errors": {"file": [_("No file uploaded.")]}}, status=400)
    md5 = Attachment.get_md5_sum(upload)
    attachment = Attachment.objects.filter(md5=md5).first()
    if attachment is None:
        attachment = Attachment.objects.create(
            file=upload,
            original_filename=upload.name,
            md5=md5,
            uploaded_by=request.user,
        )
    return JsonResponse({"id": attachment.pk})
