import hashlib
import posixpath

from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class ContentAddressedStorage(FileSystemStorage):
    """Names each file by the SHA-256 of its bytes, so identical images are stored once.

    The client-supplied filename is discarded; only its directory (from
    `upload_to`) and lowercased extension are kept.
    """

    def save(self, name, content, max_length=None):
        if name is None:
            name = content.name
        if not hasattr(content, "chunks"):
            content = File(content, name)

        digest = hashlib.sha256()
        for chunk in content.chunks():
            digest.update(chunk)
        content.seek(0)

        directory = posixpath.dirname(name.replace("\\", "/"))
        extension = posixpath.splitext(name)[1].lower()
        name = posixpath.join(directory, digest.hexdigest() + extension)

        if self.exists(name):
            return name
        return super().save(name, content, max_length=max_length)
