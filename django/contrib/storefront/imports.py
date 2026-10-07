import logging
import os
import shutil
import tarfile
import tempfile
import zipfile
import zlib

from django.core.files import File
from django.utils.translation import gettext as _

from .exceptions import InvalidImageArchive
from .models import Product, ProductImage

logger = logging.getLogger("django.contrib.storefront")


class ImageImporter:
    def handle(self, dirname):
        image_dir = self._extract_images(dirname)
        if not image_dir:
            raise InvalidImageArchive(_("%s is not a valid image archive") % dirname)
        num_processed = 0
        try:
            for filename in sorted(os.listdir(image_dir)):
                if self._process_image(image_dir, filename):
                    num_processed += 1
        finally:
            if image_dir != dirname:
                shutil.rmtree(image_dir)
        logger.info("Finished image import: %d imported", num_processed)
        return num_processed

    def _process_image(self, image_dir, filename):
        upc = os.path.splitext(filename)[0]
        try:
            product = Product.objects.get(upc=upc)
        except Product.DoesNotExist:
            logger.warning("No item matching upc='%s'", upc)
            return False
        with open(os.path.join(image_dir, filename), "rb") as image_file:
            ProductImage.objects.create(
                product=product, original=File(image_file, name=filename)
            )
        return True

    def _extract_images(self, dirname):
        """
        Returns path to directory containing images in dirname if successful.
        Returns empty string if dirname does not exist, or could not be opened.
        Assumes that if dirname is a directory, then it contains images.
        If dirname is an archive (tar/zip file) then the path returned is to a
        temporary directory that should be deleted when no longer required.
        """
        if os.path.isdir(dirname):
            return dirname

        ext = os.path.splitext(dirname)[1]
        if ext in [".gz", ".tar"]:
            image_dir = tempfile.mkdtemp()
            try:
                tar_file = tarfile.open(dirname)
                tar_file.extractall(image_dir)
                tar_file.close()
                return image_dir
            except (tarfile.TarError, zlib.error):
                return ""
        elif ext == ".zip":
            image_dir = tempfile.mkdtemp()
            try:
                zip_file = zipfile.ZipFile(dirname)
                zip_file.extractall(image_dir)
                zip_file.close()
                return image_dir
            except (zlib.error, zipfile.BadZipfile, zipfile.LargeZipFile):
                return ""
        return ""
