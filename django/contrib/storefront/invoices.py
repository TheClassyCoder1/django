import json
import logging

from django.template import Context, Engine

from .exceptions import ReportTemplateNotDefined
from .models import Report, ReportTemplate

logger = logging.getLogger("django.contrib.storefront")


def render_document(template, data):
    engine = Engine(autoescape=True)
    return engine.from_string(template.decode()).render(Context(data)).encode()


class InvoiceReport:
    _invoice_report_name = "invoice"

    def generate(self, order):
        data = {
            "number": order.number,
            "customer": order.customer.get_username(),
            "total": order.total,
            "created": order.created,
        }
        return self._get_invoice_content(data)

    def _get_invoice_content(self, data):
        try:
            report = Report.objects.get(name=self._invoice_report_name)
            template = report.templates.filter(default=True).first()
        except (Report.DoesNotExist, ReportTemplate.DoesNotExist) as e:
            raise ReportTemplateNotDefined(
                "Template for invoice report is not defined!"
            ) from e
        logger.info(
            "Using report {} and template {}".format(
                report.name, template.template.path
            )
        )
        template_content = b""
        with open(template.template.path, "rb") as f:
            template_content = f.read()

        # Make sure data is JSON-serializable
        data = json.loads(json.dumps(data, default=str))
        result = render_document(
            template=template_content,
            data=data,
        )
        return result
