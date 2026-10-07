import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .validators import validate_import_size

PROTECTED_CATALOG_FIELDS = ["id", "created", "owner"]


class CatalogImportForm(forms.Form):
    catalog_file = forms.FileField(required=False, validators=[validate_import_size])
    direct_input = forms.CharField(widget=forms.Textarea, required=False)
    public = forms.BooleanField(required=False)
    protected = forms.BooleanField(required=False)

    def clean(self):
        data = super().clean()

        # The key can be missing based on particular upload
        # conditions. Code defensively for it here...
        catalog_file = data.get("catalog_file", None)
        catalog_raw = data.get("direct_input", None)

        if catalog_raw and catalog_file:
            raise ValidationError(_("Cannot specify both file and direct input."))
        if not catalog_raw and not catalog_file:
            raise ValidationError(_("No input was provided for the catalog content."))
        try:
            if catalog_file:
                catalog_str = self.files["catalog_file"].read()
            else:
                catalog_str = data["direct_input"]
            catalog = json.loads(catalog_str)

            if data["public"]:
                catalog["visibility"] = "public"
            else:
                catalog["visibility"] = "private"

            catalog["protected"] = data["protected"]

            for protected_prop in PROTECTED_CATALOG_FIELDS:
                catalog.pop(protected_prop, None)

            data["catalog"] = catalog
        except Exception as e:
            msg = _("There was a problem loading the catalog: %s.") % e
            raise forms.ValidationError(msg)

        return data


class SalesReportForm(forms.Form):
    category = forms.IntegerField(min_value=1)
    limit = forms.IntegerField(min_value=1, max_value=100)
