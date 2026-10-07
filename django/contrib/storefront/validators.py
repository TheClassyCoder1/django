from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _

MAX_CATALOG_IMPORT_SIZE = 2 * 1024 * 1024


def validate_import_size(value):
    if value.size > MAX_CATALOG_IMPORT_SIZE:
        raise ValidationError(
            _("Catalog files may not be larger than %s.")
            % filesizeformat(MAX_CATALOG_IMPORT_SIZE)
        )
