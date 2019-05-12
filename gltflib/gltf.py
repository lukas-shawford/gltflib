import struct
import warnings
from os import path
from urllib.parse import urlparse
from typing import Type, TypeVar, List, Sequence, Optional, Set, BinaryIO
from .gltf_resource import GLTFResource, FileResource, ExternalResource, GLBResource, GLB_JSON_CHUNK_TYPE,\
    GLB_BINARY_CHUNK_TYPE
from .models import GLTFModel, Buffer, BufferView
from .utils import padbytes


T = TypeVar('T', bound='GLTF')


class GLTF:
    GLB_HEADER_BYTELENGTH = 12

    def __init__(self, model: GLTFModel = None, resources: List[GLTFResource] = None):
        self.model = model
        self._resources = resources[:] if resources is not None else []
        self._glb_resources: List[GLBResource] = []
        self._hash_resource_uris()

    @classmethod
    def load(cls: Type[T], filename: str, load_file_resources=False, resources: List[GLTFResource] = None) -> T:
        """
        Loads a GLTF or GLB model from a filename. The model format will be inferred from the filename extension.
        :param filename: Path to the GLTF or GLB file
        :param load_file_resources: If True, external file resources that are not provided via the "resources"
            array will be loaded from the filesystem. The paths are assumed to be relative to the GLTF file.
        :param resources: Optional list of pre-loaded resources. Any resources referenced in the GLTF file that are
            present in the resources array will be used instead of loading those resources from the external
            source.
        :return: GLTF instance
        """
        ext = path.splitext(filename)[1].lower()
        if ext == '.gltf':
            return cls.load_gltf(filename, load_file_resources, resources)
        elif ext == '.glb':
            return cls.load_glb(filename, load_file_resources, resources)
        raise RuntimeError(f'File format could not be inferred from filename: {filename}. Ensure the filename has '
                           f'the appropriate extension (.gltf or .glb), or call load_gltf or load_glb directly if '
                           f'the filename does not follow the convention but the format is known.')

    @classmethod
    def load_gltf(cls: Type[T], filename: str, load_file_resources=False, resources: List[GLTFResource] = None) -> T:
        """
        Loads a model in GLTF format from a filename
        :param filename: Path to the GLTF file
        :param load_file_resources: If True, external file resources that are not provided via the "resources"
            array will be loaded from the filesystem. The paths are assumed to be relative to the GLTF file.
        :param resources: Optional list of pre-loaded resources. Any resources referenced in the GLTF file that are
            present in the resources array will be used instead of loading those resources from the external
            source.
        :return: GLTF instance
        """
        gltf = GLTF(model=None, resources=resources)
        with open(filename, 'r') as f:
            data = f.read()
            gltf.model = GLTFModel.from_json(data)
        basepath = path.dirname(filename)
        gltf._load_file_resources(basepath, load_file_resources)
        return gltf

    @classmethod
    def load_glb(cls: Type[T], filename: str, load_file_resources=False, resources: List[GLTFResource] = None) -> T:
        """
        Loads a model in GLB format from a filename
        :param filename: Path to the GLB file
        :param load_file_resources: If True, external file resources that are not provided via the "resources"
            array will be loaded from the filesystem. The paths are assumed to be relative to the GLTF file.
        :param resources: Optional list of pre-loaded resources. Any resources referenced in the GLTF file that are
            present in the resources array will be used instead of loading those resources from the external
            source.
        :return: GLTF instance
        """
        gltf = GLTF(model=None, resources=resources)
        with open(filename, 'rb') as f:
            gltf._load_glb(f)
        basepath = path.dirname(filename)
        gltf._load_file_resources(basepath, load_file_resources)
        return gltf

    def export(self, filename: str, save_file_resources=True) -> None:
        """
        Exports the model to a GLTF or GLB (inferred from filename extension).
        :param filename: Output filename
        :param save_file_resources: If True, external file resources present in the resources list will be saved
        """
        ext = path.splitext(filename)[1].lower()
        if ext == '.gltf':
            return self.export_gltf(filename, save_file_resources)
        elif ext == '.glb':
            return self.export_glb(filename, embed_buffer_resources=True, embed_image_resources=True,
                                   save_file_resources=save_file_resources)
        raise RuntimeError(f'File format could not be inferred from filename: {filename}. Ensure the filename has '
                           f'the appropriate extension (.gltf or .glb), or call export_gltf or export_glb directly.')

    def export_gltf(self, filename: str, save_file_resources=True) -> None:
        """
        Exports the model to a GLTF file
        :param filename: Output filename
        :param save_file_resources: If True, external file resources present in the resources list will be saved
        """
        if any(isinstance(resource, GLBResource) for resource in self._resources):
            raise TypeError("Model may not contain resources of type GLBResource when exporting to GLTF. "
                            "Convert the GLBResource to FileResource or EmbeddedResource prior to exporting to GLTF, "
                            "or export to GLB instead.")
        data = self.model.to_json()
        with open(filename, 'w') as f:
            f.write(data)
        if save_file_resources:
            self._validate_resources()
            basepath = path.dirname(filename)
            self._export_file_resources(basepath)

    def export_glb(self, filename: str, embed_buffer_resources=True, embed_image_resources=True,
                   save_file_resources=True) -> None:
        """
        Exports the model to a GLB file
        :param filename: Output filename
        :param embed_buffer_resources: If True, buffer resources will be embedded in the GLB. The default value is True.
            Note that only file and data URI resources will be converted. External network resources will be left as
            they are. Note: If there are any buffers that use file resources which you wish to leave as external file
            references, set this to False and convert the resources individually before calling export_glb.
        :param embed_image_resources: If True, image resources will be embedded in the GLB. The default value is True.
            Note that only file and data URI resources will be converted. External network resources will be left as
            they are. Note: If there are any images that use file resources which you wish to leave as external file
            references, set this to False and convert the resources individually before calling export_glb.
        :param save_file_resources: If True, any external file resources that are not being embedded in the GLB
            will be saved (in addition to the main GLB file). The default value is True.
        """
        if embed_buffer_resources:
            self._embed_buffer_resources()
        if embed_image_resources:
            self._embed_image_resources()
        with open(filename, 'wb') as f:
            self._export_glb(f)
        if save_file_resources:
            self._validate_resources()
            basepath = path.dirname(filename)
            self._export_file_resources(basepath)

    @property
    def resources(self) -> Sequence[GLTFResource]:
        return self._resources[:] + self._glb_resources

    def get_resource(self, uri: str) -> GLTFResource:
        if uri is None:
            return self._glb_resources[0] if len(self._glb_resources) > 0 else None
        return self._resourcemap[uri]

    def get_glb_resource(self, resource_type: int = GLB_BINARY_CHUNK_TYPE) -> GLBResource:
        for resource in self._glb_resources:
            if resource.resource_type == resource_type:
                return resource

    def get_glb_resources_of_type(self, resource_type: int) -> List[GLBResource]:
        return [resource for resource in self._glb_resources if resource.resource_type == resource_type]

    def get_glb_resources(self) -> List[GLBResource]:
        return self._glb_resources[:]

    def add_resource(self, resource: GLTFResource) -> None:
        if isinstance(resource, GLBResource):
            self._glb_resources.append(resource)
        else:
            self._resources.append(resource)
            self._hash_resource_uris()

    def remove_resource(self, resource: GLTFResource) -> None:
        self._resources.remove(resource)
        self._hash_resource_uris()

    def remove_resource_by_uri(self, uri: str) -> None:
        if uri is None:
            raise ValueError('Parameter must be a uri must not be None.')
        if uri not in self._resourcemap:
            return
        resource = self._resourcemap[uri]
        self.remove_resource(resource)

    def _hash_resource_uris(self) -> None:
        self._resourcemap = dict()
        if self._resources is None:
            return
        for resource in self._resources:
            if resource.uri in self._resourcemap and not isinstance(resource, GLBResource):
                raise RuntimeError('Multiple resources with same URI are not allowed (except for GLB resources)')
            if isinstance(resource, GLBResource):
                if resource.uri is not None:
                    raise RuntimeError('GLB embedded resources must not have a URI')
                self._glb_resources.append(resource)
            else:
                self._resourcemap[resource.uri] = resource

    def _get_resource_uris_from_model(self) -> Set:
        uris = set()
        if self.model.buffers is not None:
            uris.update([buffer.uri for buffer in self.model.buffers if buffer.uri is not None])
        if self.model.images is not None:
            uris.update([image.uri for image in self.model.images if image.uri is not None])
        return uris

    def _load_file_resources(self, basepath: str, autoload=False) -> None:
        self._resources = self._resources or []
        for uri in self._get_resource_uris_from_model():
            if uri not in self._resourcemap:
                resource = _get_resource(uri, basepath, autoload)
                if resource is not None:
                    self._resources.append(resource)
                    self._resourcemap[uri] = resource

    def _validate_resources(self) -> None:
        for uri in self._get_resource_uris_from_model():
            if self._resourcemap is None or uri not in self._resourcemap:
                raise RuntimeError(f'Missing resource: "{uri}". When exporting a model with save_file_resources set '
                                   f'to True, all external resources must be provided via the resources dictionary.')

    def _export_file_resources(self, basepath: str) -> None:
        if self._resources is None:
            return
        for resource in self._resources:
            if isinstance(resource, FileResource):
                resource.export(basepath)

    def _load_glb(self, f: BinaryIO) -> None:
        bytelen = self._load_glb_header(f)
        self._load_glb_chunks(f)
        pos = f.tell()
        if pos != bytelen:
            warnings.warn(f'GLB file length specified in file header ({bytelen}) does not match number of bytes '
                          f'read ({pos}). The GLB file may be corrupt.', RuntimeWarning)

    def _load_glb_header(self, f: BinaryIO) -> int:
        b = f.read(self.GLB_HEADER_BYTELENGTH)
        magic = b[0:4]
        if magic != b'glTF':
            raise RuntimeError('File is not a valid GLB file')
        version, = struct.unpack_from('<I', b, 4)
        if version != 2:
            raise RuntimeError(f'Unsupported GLB file version: "{version}". Only version 2 is currently supported')
        bytelen, = struct.unpack_from('<I', b, 8)
        return bytelen

    def _load_glb_chunks(self, f: BinaryIO) -> None:
        while self._load_glb_chunk(f):
            pass

    def _load_glb_chunk(self, f: BinaryIO) -> bool:
        b = f.read(8)
        if b == b'':
            return False
        if len(b) != 8:
            raise RuntimeError(f'Unexpected EOF when processing GLB chunk header. Chunk header must be 8 bytes, '
                               f'got {len(b)} bytes.')
        chunk_length, = struct.unpack_from('<I', b, 0)
        chunk_type = b[4:8]
        if chunk_type == b'JSON':
            self._load_glb_json_chunk_body(f, chunk_length)
        elif chunk_type == b'BIN\x00':
            self._load_glb_binary_chunk_body(f, chunk_length)
        # Per spec, ignore unknown chunk types to enable glTF extensions to reference additional chunks with new types
        # TODO: Rather than ignoring them, load them anyway and specify the resource_type when instantiating GLBResource
        return True

    def _load_glb_json_chunk_body(self, f: BinaryIO, bytelen: int) -> None:
        if bytelen == 0:
            raise RuntimeError('JSON chunk may not be empty')
        b = f.read(bytelen)
        if len(b) != bytelen:
            raise RuntimeError(f'Unexpected EOF when parsing JSON chunk body. The GLB file may be corrupt.')
        model_json = b.decode('utf-8').strip()
        self.model = GLTFModel.from_json(model_json)
        # TODO: GLBs may reference external file resources (in addition to the embedded binary chunk) - those should be
        #  loaded here.

    def _load_glb_binary_chunk_body(self, f: BinaryIO, bytelen: int) -> None:
        if bytelen == 0:
            raise RuntimeError('Binary chunk body may not be empty')
        b = f.read(bytelen)
        if len(b) != bytelen:
            raise RuntimeError(f'Unexpected EOF when parsing binary chunk body. The GLB file may be corrupt.')
        resource = GLBResource(b)
        self._glb_resources.append(resource)

    def _export_glb(self, f: BinaryIO):
        self._prepare_glb()
        self._write_glb_header(f)
        self._write_glb_body(f)

    def _prepare_glb(self):
        json_bytes = bytearray(self.model.to_json(separators=(',', ':')).encode('utf-8'))
        json_len = padbytes(json_bytes, 4, b'\x20')
        json_chunk = (json_len, GLB_JSON_CHUNK_TYPE, json_bytes)
        self._chunks = [json_chunk]
        for resource in self.get_glb_resources():
            data = resource.data
            bytelen = len(data)
            if bytelen % 4 != 0:
                data = bytearray(data)
                bytelen = padbytes(data, 4)
            chunk = (bytelen, resource.resource_type, data)
            self._chunks.append(chunk)

    def _write_glb_header(self, f: BinaryIO):
        chunk_header_len = 8
        bytelen = self.GLB_HEADER_BYTELENGTH + sum(chunk[0] + chunk_header_len for chunk in self._chunks)
        output = bytearray()
        output.extend(b'glTF')
        output.extend(struct.pack('<I', 2))
        output.extend(struct.pack('<I', bytelen))
        f.write(output)

    def _write_glb_body(self, f: BinaryIO):
        for chunk in self._chunks:
            bytelen, chunk_type, data = chunk
            f.write(struct.pack('<I', bytelen))
            f.write(struct.pack('<I', chunk_type))
            f.write(data)

    def _embed_buffer_resources(self):
        glb_resource = self.get_glb_resource()
        data = bytearray()
        offset = 0 if glb_resource is None else len(glb_resource.data)
        if self.model.buffers is not None:
            keep_buffers = []
            for i, buffer in enumerate(self.model.buffers):
                if buffer.uri is None:
                    keep_buffers.append(buffer)
                    continue
                resource = self.get_resource(buffer.uri)
                if resource is None:
                    raise RuntimeError(f'Missing resource: "{buffer.uri}" (referenced in buffer with index {i})')
                elif isinstance(resource, FileResource):
                    if not resource.loaded:
                        resource.load()
                    data.extend(resource.data)
                    bytelen = padbytes(data, 4, offset=offset)
                    self._embed_buffer_views(i, offset)
                    offset += bytelen
                else:
                    keep_buffers.append(buffer)
                # TODO: Handle data URIs
            self.model.buffers = keep_buffers
        if len(data) > 0:
            self._create_or_extend_glb_resource(data)

    def _embed_image_resources(self):
        glb_resource = self.get_glb_resource()
        data = bytearray()
        offset = 0 if glb_resource is None else len(glb_resource.data)
        if self.model.images is not None:
            for i, image in enumerate(self.model.images):
                # TODO: Handle data URIs
                if image.uri is None:
                    continue
                resource = self.get_resource(image.uri)
                if resource is None:
                    raise RuntimeError(f'Missing resource: "{image.uri}" (referenced in image with index {i})')
                elif isinstance(resource, FileResource):
                    if not resource.loaded:
                        resource.load()
                    data.extend(resource.data)
                    bytelen = padbytes(data, 4, offset=offset)
                    image.uri = None
                    image.bufferView = self._create_embedded_image_buffer_view(offset, len(resource.data))
                    image.mimeType = resource.mimetype
                    offset += bytelen
        if len(data) > 0:
            self._create_or_extend_glb_resource(data)

    def _get_or_create_glb_buffer(self):
        if self.model.buffers is None or len(self.model.buffers) == 0:
            buffer = Buffer(byteLength=0)
            self.model.buffers = [buffer]
            return buffer
        first_buffer = self.model.buffers[0]
        if first_buffer.uri is None:
            # Validate all other buffers have a uri defined. Per the spec, the GLB embedded buffer must be the first in
            # the list. Issue a warning if this is not the case.
            for i, buffer in enumerate(self.model.buffers[1:]):
                if buffer.uri is None:
                    warnings.warn(f'Buffer at index {i} has its uri undefined, but it is not the first buffer in the '
                                  f'list. This is not valid per the specification. The GLB-stored buffer must be the '
                                  f'first buffer in the buffers array.', RuntimeWarning)
            return first_buffer
        # Create a GLB-stored buffer with an undefined URI and insert it as the first buffer in the list.
        buffer = Buffer(byteLength=0)
        self.model.buffers.insert(0, buffer)
        return buffer

    def _create_or_extend_glb_resource(self, data: bytearray):
        glb_resource = self.get_glb_resource()
        if glb_resource is None:
            glb_resource = GLBResource(data)
            self.add_resource(glb_resource)
        else:
            # Merge new data with the data we already have in the existing GLBResource
            data[0:0] = glb_resource.data
            # Remove the old GLB resource
            self._glb_resources.remove(glb_resource)
            # Create a new GLBResource with the merged data and add it to the _glb_resources array
            glb_resource = GLBResource(data)
            self._glb_resources.insert(0, glb_resource)
        buffer = self._get_or_create_glb_buffer()
        buffer.byteLength = len(data)

    def _embed_buffer_views(self, buffer_index, glb_offset):
        if self.model.bufferViews is not None:
            for buffer_view in self.model.bufferViews:
                if buffer_view.buffer == buffer_index:
                    buffer_view.buffer = 0
                    buffer_view.byteOffset += glb_offset

    def _create_embedded_image_buffer_view(self, byte_offset: int, byte_length: int):
        buffer_view = BufferView(buffer=0, byteOffset=byte_offset, byteLength=byte_length)
        if self.model.bufferViews is None or len(self.model.bufferViews) == 0:
            self.model.bufferViews = [buffer_view]
            return 0
        self.model.bufferViews.append(buffer_view)
        return len(self.model.bufferViews) - 1


def _get_resource(uri, basepath: str, autoload=False) -> Optional[GLTFResource]:
    scheme, netloc, urlpath, params, query, fragment = urlparse(uri)
    if netloc:
        return ExternalResource(uri)
    elif not scheme:
        return FileResource(uri, basepath, autoload)
    return None
