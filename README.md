# gltflib

Library for parsing, creating, and converting glTF 2.0 files in Python 3.6+.

## Overview

This library is intended for working with glTF 2.0 at a fairly low level, meaning you are
responsible for managing the actual geometry data yourself. This library facilitates saving
this data into a properly formatted glTF/GLB file. It also helps with converting resources
inside a glTF/GLB file between external binary files and embedded GLB resources.

## Usage

The examples below illustrate how to use this library for a couple sample scenarios. The
example models come from the Khronos glTF-Sample-Models repository available here:

[https://github.com/KhronosGroup/glTF-Sample-Models](https://github.com/KhronosGroup/glTF-Sample-Models)

### Parsing a glTF 2.0 Model

To load a glTF 2.0 model:

```python
from gltflib import GLTF

gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF/BoxTextured.gltf')
```

The `GLTF.load` static method supports loading both the JSON-based `.gltf` format, as well
as the binary `.glb` format. The type of the file will be determined based on the filename
extension. Alternatively, you can use `GLTF.load_gltf(filename)` or `GLTF.load_glb(filename)`.

After loading, you can inspect the model structure by accessing the `model` property:

```python
print(gltf.model)
# GLTFModel(extensions=None, extras=None, accessors=[Accessor(extensions=None, extras=None, name=None, bufferView=0, byteOffset=0, componentType=5123, ...
```

You can also inspect the various model properties:

```python
print(gltf.model.buffers[0].uri)
# BoxTextured0.bin
```

A glTF 2.0 model may contain resources, such as vertex geometry or image textures. These
resources can be embedded as part of the model file, or (as with the above example) be
referenced as external file resources.

In either case, the resources are parsed alongside the model structure into the `resources`
property after loading a model:

```python
print(gltf.resources)
# [FileResource(CesiumLogoFlat.png), FileResource(BoxTextured0.bin)]
```

Note that the actual content of these external file resources is *not* loaded by default
when loading a model. You can load the resource into memory in one of two ways. One way
is to call the `load()` method on the resource:

```python
resource = gltf.resources[0]
resource.load()     # Assumes resource is a FileResource
```

Another way is to pass the `load_file_resources` flag when calling `GLTF.load()`:

```python
gltf = GLTF.load(filename, load_file_resources=True)
```

In either case, now the file resource data can be accessed via the `data` property:

```python
print(resource.data)
# b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\x00\x00\...
```

Embedded resources in binary GLB files are also parsed into the `resources` list, but
they will be of type `GLBResource` instead of `FileResource`:

```python
glb = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF-Binary/BoxTextured.glb')
print(glb.resources)
# [<gltflib.gltf_resource.GLBResource object at 0x7f03db7c1400>]
```

For embedded resources, the content is parsed into memory automatically. The binary data
can be accessed using the `data` property:

```python
resource = glb.resources[0]
print(resource.data)
# b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\x00\x00\...'
```

### Exporting a glTF 2.0 Model

To export a model, call the `GLTF.export()` instance method in the `GLTF` class.

The example below creates a simple glTF 2.0 mode in memory (consisting of a single
triangle), then exports it as a glTF file named `triangle.gltf` (alongside with an
external file resource named `vertices.bin`):

```python
import struct
import operator
from gltflib import (
    GLTF, GLTFModel, Asset, Scene, Node, Mesh, Primitive, Attributes, Buffer, BufferView, Accessor, AccessorType,
    BufferTarget, ComponentType, GLBResource, FileResource)

vertices = [
    (-4774424.719997984, 4163079.2597148907, 671001.6353722484),
    (-4748098.650098154, 4163079.259714891, 837217.8990777463),
    (-4689289.5292739635, 4246272.966707474, 742710.4976137652)
]

vertex_bytearray = bytearray()
for vertex in vertices:
    for value in vertex:
        vertex_bytearray.extend(struct.pack('f', value))
bytelen = len(vertex_bytearray)
mins = [min([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]
maxs = [max([operator.itemgetter(i)(vertex) for vertex in vertices]) for i in range(3)]
model = GLTFModel(
    asset=Asset(version='2.0'),
    scenes=[Scene(nodes=[0])],
    nodes=[Node(mesh=0)],
    meshes=[Mesh(primitives=[Primitive(attributes=Attributes(POSITION=0))])],
    buffers=[Buffer(byteLength=bytelen, uri='vertices.bin')],
    bufferViews=[BufferView(buffer=0, byteOffset=0, byteLength=bytelen, target=BufferTarget.ARRAY_BUFFER.value)],
    accessors=[Accessor(bufferView=0, byteOffset=0, componentType=ComponentType.FLOAT.value, count=len(vertices),
                        type=AccessorType.VEC3.value, min=mins, max=maxs)]
)

resource = FileResource('vertices.bin', data=vertex_bytearray)
gltf = GLTF(model=model, resources=[resource])
gltf.export('triangle.gltf')
```

As with `load`, the `export` method infers the format based on the filename extension
(`.gltf` vs `.glb`). However, you can also call `export_gltf` or `export_glb` to manually
force the format.

In the above example, the export will produce two files: `triangle.gltf` and `vertices.bin`.
However, it is possible to bypass saving external file resources by setting the
`save_file_resources` flag to `False` when calling `export`:

```python
gltf.export('triangle.gltf', save_file_resources=False)
```

To export the model as a binary GLB instead, simply change the extension when calling
`export`, or use `export_glb`:

```python
gltf.export('triangle.glb')
```

Note that when exporting as a GLB, all resources will be embedded by default (even if
they were instantiated as a `FileResource`). This is generally the desired behavior when
saving as a GLB.

However, it is possible to force some or all resources to remain external when exporting
a GLB. To do so, you must call `export_glb` (instead of `export`), and setting either
`embed_buffer_resources` or `embed_image_resources` (or both) to `False`:

```python
resource = FileResource('vertices.bin', data=vertex_bytearray)
gltf = GLTF(model=model, resources=[resource])
gltf.export_glb('triangle.glb', embed_buffer_resources=False, embed_image_resources=False)
```

In this case, you will also need to ensure that the associated buffers still have the
appropriate `uri` set in the model:

```python
model = GLTFModel(
    ...,
    buffers=[Buffer(byteLength=bytelen, uri='vertices.bin')],
```

The model will be exported as a binary GLB, but with external file resources. These
file resources will be saved by default when exporting the model. However, it is also
possible to bypass saving external file resources by setting the `save_file_resources`
to `False` when calling `export_glb`:

```python
gltf.export_glb('triangle.glb', embed_buffer_resources=False, embed_image_resources=False,
                save_file_resources=False)
```

### Converting Between glTF and GLB

To convert a glTF model to GLB, simply load it and export it using the `glb` extension:

```python
from gltflib import GLTF

gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF/BoxTextured.gltf')
gltf.export('BoxTextured.glb')
```

This will automatically convert all external file resources to become embedded GLB
resources.

* TODO: Reverse conversion possible?
* TODO: Add capability to convert resources without having to reconstruct the model
