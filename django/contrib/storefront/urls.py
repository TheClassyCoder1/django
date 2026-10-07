from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from . import views

app_name = "storefront"

urlpatterns = [
    path(
        "fulfillment/shipments/<int:pk>/",
        staff_member_required(views.ShipmentDetailView.as_view()),
        name="shipment_detail",
    ),
    path(
        "customers/<str:customer_username>/orders/",
        staff_member_required(views.CustomerOrdersView.as_view()),
        name="customer_orders",
    ),
    path("reports/sales/", views.sales_report, name="sales_report"),
    path("catalog/import/", views.import_catalog, name="import_catalog"),
    path("attachments/", views.upload_attachment, name="upload_attachment"),
]
