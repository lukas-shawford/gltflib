import json
import warnings
from dataclasses import dataclass, asdict
from dataclasses_json import DataClassJsonMixin
from typing import List, Optional, Type, TypeVar
from ..utils import del_none, RequiredMixin, MISSING
from .accessor import Accessor
from .animation import Animation
from .asset import Asset
from .base_model import BaseModel
from .buffer import Buffer
from .buffer_view import BufferView
from .camera import Camera
from .image import Image
from .material import Material
from .mesh import Mesh
from .node import Node
from .sampler import Sampler
from .scene import Scene
from .texture import Texture


T = TypeVar('T', bound='GLTFModel')


@dataclass
class GLTFModel(DataClassJsonMixin, BaseModel, RequiredMixin):
    accessors: Optional[List[Accessor]] = None
    animations: Optional[List[Animation]] = None
    asset: Asset = MISSING
    buffers: Optional[List[Buffer]] = None
    bufferViews: Optional[List[BufferView]] = None
    cameras: Optional[List[Camera]] = None
    images: Optional[List[Image]] = None
    materials: Optional[List[Material]] = None
    meshes: Optional[List[Mesh]] = None
    nodes: Optional[List[Node]] = None
    samplers: Optional[List[Sampler]] = None
    scene: Optional[int] = None
    scenes: Optional[List[Scene]] = None
    textures: Optional[List[Texture]] = None

    def to_json(self, **kwargs):
        data = del_none(asdict(self))
        return json.dumps(data, **kwargs)

    @classmethod
    def from_json(cls: Type[T],
                  s: str,
                  *,
                  encoding=None,
                  parse_float=None,
                  parse_int=None,
                  parse_constant=None,
                  infer_missing=False,
                  **kw) -> T:
        # The dataclasses_json library emits a runtime warning for missing non-optional fields. For the purposes of
        # this library, we prefer these to be treated as errors. This class method simply calls the base method with
        # all the same arguments, except it records warnings and raises a TypeError if any warnings are encountered.
        # If this behavior is ever changed in the dataclasses_json library, this class method may be removed since it
        # does not perform any additional processing (it simply passes all the arguments down to the base method).
        with warnings.catch_warnings(record=True) as ws:
            model = super(GLTFModel, cls).from_json(
                s,
                encoding=encoding,
                parse_float=parse_float,
                parse_int=parse_int,
                parse_constant=parse_constant,
                infer_missing=infer_missing,
                **kw)
            if len(ws) > 0:
                msg = '\n'.join([str(w.message) for w in ws])
                raise TypeError(f"Warnings were encountered when decoding the model from JSON:\n{msg}")
            return model
