from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Optional, Dict, Any


@dataclass
@dataclass_json
class BaseModel:
    """
    Base model for all GLTF2 models

    Properties:
    extensions (object): Dictionary object with extension-specific objects. (Optional)
    extras (any) Application-specific data. (Optional)
    """
    extensions: Optional[Dict] = None
    extras: Optional[Any] = None
