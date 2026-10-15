import shutil
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from dishbook.models import Profile, Recipe

LEGACY_MEDIA_DIR = Path(settings.BASE_DIR) / "media"
FIELDS = [(Recipe, "recipes/"), (Profile, "profiles/")]


class Command(BaseCommand):
    help = (
        "Move photos into MEDIA_ROOT under content-hash names, collapse duplicates, "
        "and delete any media file no recipe or profile references."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report changes without making them.")

    def handle(self, *args, dry_run=False, **options):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        missing = []

        with transaction.atomic():
            for model, upload_dir in FIELDS:
                for obj in model.objects.exclude(photo=""):
                    old_name = obj.photo.name
                    source = self._locate(old_name)
                    if source is None:
                        missing.append(f"{model.__name__} {obj.pk}: {old_name}")
                        continue
                    if dry_run:
                        continue
                    with source.open("rb") as f:
                        new_name = default_storage.save(upload_dir + source.name, File(f))
                    if new_name != old_name:
                        obj.photo.name = new_name
                        obj.save(update_fields=["photo"])

        referenced = {
            media_root / name
            for model, _ in FIELDS
            for name in model.objects.exclude(photo="").values_list("photo", flat=True)
        }
        orphans = [p for p in media_root.rglob("*") if p.is_file() and p.resolve() not in referenced]

        if dry_run:
            self.stdout.write(f"Would delete {len(orphans)} unreferenced file(s) in {media_root}.")
        else:
            for path in orphans:
                path.unlink()
            self.stdout.write(f"Deleted {len(orphans)} unreferenced file(s) in {media_root}.")

        if LEGACY_MEDIA_DIR.is_dir() and LEGACY_MEDIA_DIR.resolve() != media_root:
            if dry_run:
                self.stdout.write(f"Would remove legacy folder {LEGACY_MEDIA_DIR}.")
            elif missing:
                self.stdout.write(f"Keeping legacy folder {LEGACY_MEDIA_DIR} because some photos were missing.")
            else:
                shutil.rmtree(LEGACY_MEDIA_DIR)
                self.stdout.write(f"Removed legacy folder {LEGACY_MEDIA_DIR}.")

        for entry in missing:
            self.stderr.write(f"Missing file for {entry}")

        total = len(referenced)
        self.stdout.write(self.style.SUCCESS(f"{total} unique photo file(s) referenced."))

    def _locate(self, name):
        """Find a photo either in MEDIA_ROOT or at its pre-MEDIA_ROOT path relative to BASE_DIR."""
        for base in (Path(settings.MEDIA_ROOT), Path(settings.BASE_DIR)):
            path = (base / name).resolve()
            if path.is_relative_to(base.resolve()) and path.is_file():
                return path
        return None
