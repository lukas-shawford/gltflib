import struct
import magic
from os import path
from abc import ABC
from typing import Optional


GLB_JSON_CHUNK_TYPE, = struct.unpack('<I', b'JSON')
GLB_BINARY_CHUNK_TYPE, = struct.unpack('<I', b'BIN\x00')


class GLTFResource(ABC):
    """
    Base class for a GLTF resource representation containing binary data. Note that depending on the resource type, the
    data may or may not actually be available to be consumed directly.
    """
    def __init__(self, uri: Optional[str], data: bytes = None):
        self._uri = uri
        self._data = data

    @property
    def uri(self):
        return self._uri

    @property
    def data(self):
        return self._data


class FileResource(GLTFResource):
    """
    GLTF resource that exists on the local filesystem. When exporting a GLTF model, all file resources will be saved to
    disk. When loading a GLTF model with load_file_resources set to True, any URIs that refer to a file will be imported
    as file resources.
    """
    def __init__(self, filename: str = None, basepath: str = None, autoload=False, data: bytes = None,
                 mimetype: str = None):
        super(FileResource, self).__init__(filename, data)
        self.filename = filename
        self._loaded = self._data is not None
        self._basepath = basepath
        self._mimetype = mimetype
        if autoload:
            self.load()

    def __repr__(self):
        return f'FileResource({self.filename})'

    @property
    def loaded(self):
        return self._loaded

    @property
    def mimetype(self):
        return self._mimetype

    def load(self, force_reload=False):
        if self._loaded and not force_reload:
            return
        if not self.filename:
            raise ValueError("Attempted to load FileResource without filename")
        filename = path.join(self._basepath, self.filename) if self._basepath is not None else self.filename
        with open(filename, 'rb') as f:
            self._data = f.read()
            self._mimetype = self._mimetype or magic.from_file(filename, mime=True)
        self._loaded = True

    def export(self, basepath: str = None) -> None:
        if not self.filename:
            raise ValueError("Attempted to export FileResource without filename")
        self.load()
        if self._data is None:
            raise ValueError("Attempted to export FileResource without data")
        basepath = basepath or self._basepath
        filename = path.join(basepath, self.filename) if basepath is not None else self.filename
        with open(filename, 'wb') as f:
            f.write(self._data)


class ExternalResource(GLTFResource):
    """
    External GLTF resource referenced by URI. These resources are assumed to exist, and will not be loaded when
    importing or saved when exporting.
    """
    def __init__(self, uri: str):
        super(ExternalResource, self).__init__(uri)

    def __repr__(self):
        return f'FileResource({self.uri})'

    @property
    def data(self):
        raise ValueError("Data is not accessible for an external GLTF resource")


class GLBResource(GLTFResource):
    """
    Embedded GLTF resource inside a Binary glTF (GLB).
    """
    def __init__(self, data: bytes, resource_type: int = GLB_BINARY_CHUNK_TYPE):
        super(GLBResource, self).__init__(None, data)
        self._resource_type = resource_type

    @property
    def resource_type(self):
        return self._resource_type
