from django.contrib.storefront.exceptions import InvalidImageArchive
from django.contrib.storefront.imports import ImageImporter
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Import product images from a directory or a tar/zip archive."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Directory or archive of images named by UPC.")

    def handle(self, *args, **options):
        try:
            num_processed = ImageImporter().handle(options["path"])
        except InvalidImageArchive as e:
            raise CommandError(str(e))
        self.stdout.write(f"Imported {num_processed} images.\n")
