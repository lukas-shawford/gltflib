# gltflib

Library for parsing, creating, and converting glTF 2.0 files in Python 3.6+.

## Overview

This library is intended for working with glTF 2.0 at a fairly low level, meaning you are
responsible for managing the actual geometry data yourself. This library facilitates saving
this data into a properly formatted glTF/GLB file. It also helps with converting resources
inside a glTF/GLB file between external files or web URLs, data URLs, and embedded GLB
resources.

## Installation

This library can be installed using pip:

```
pip install gltflib
```

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

The reverse conversion is also possible, though with some caveats. Since a non-binary
glTF model may not have embedded binary data, the `GLBResource` must first be converted
to a different resource type. The section on **Resources** below goes into more details,
but here is a quick example where the `GLBResource` is first converted to a `FileResource`
with the filename `BoxTextured.bin` prior to exporting to glTF:

```python
from gltflib import GLTF

gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF-Binary/BoxTextured.glb')
glb_resource = gltf.get_glb_resource()
gltf.convert_to_file_resource(glb_resource, 'BoxTextured.bin')
gltf.export('BoxTextured.gltf')
```

Note that a GLB file typically contains a single binary GLB chunk that combines data
from multiple buffers (which are then consumed by multiple buffer views, images, and
accessors). Currently, when converting a GLB to glTF, the entire GLB chunk can be
converted to a resource of a different type, but the resource cannot be split out into
multiple resources (e.g., separate resource per buffer).

### Resources

glTF and GLB models can refer to embedded or external resources (via the buffer or image
URIs, or in the case of GLB, by leaving the first buffer's URI undefined). These
resources are represented in this library using subclasses of the `GLTFResource` base
class. These resources will be parsed when loading a model, and must be properly
instantiated and added to the model prior to exporting.

There are 4 resource types that are supported by this library:

* `FileResource`: File resources are resources that refer to a file path.
* `Base64Resource`: Resources that are embedded directly in the glTF (or GLB) file
using a Base64-encoded data URI.
* `GLBResource`: Used only by GLB files, this resource type represents the binary GLB
chunk that is embedded directly in the GLB file.
* `ExternalResource`: External resources refer to external web URLs.

A reference to a particular resource can be obtained if its URI is known by
calling `get_resource`:

```python
gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF/BoxTextured.gltf')
logo = gltf.get_resource('CesiumLogoFlat.png')
print(logo)
# FileResource(CesiumLogoFlat.png)
```

Alternatively, a list of all resources in a model can be obtained using the
`resources` list on the loaded model:

```python
gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF/BoxTextured.gltf')
print(gltf.resources)
# [FileResource(CesiumLogoFlat.png), FileResource(BoxTextured0.bin)]
```

The `GLTF` class provides helper methods that can be used to convert a resource
from one type to another. Some of these methods require some additional information
to do the conversion; for instance, the filename when converting to a `FileResource`,
or the MIME type when converting to a `Base64Resource`.

The sections below go into more detail about each resource type, including their
caveats and limitations, as well as how to convert a given resource to that type.

#### File Resources

File resources are denoted using the `FileResource` class, and represent resources
that refer to a file path (generally a relative path, though absolute file paths are
also supported).

When loading a model, these resources are parsed by looking at the `uri` property on
buffers and images; however, their content is not automatically loaded unless the
`load_file_resources` flag is set to `True` when calling `GLTF.load()`:

```python
gltf = GLTF.load(filename, load_file_resources=True)
```

Alternatively, the `load()` method can be called on a `FileResource` instance to load
the data into memory:

```python
resource = FileResource('triangleWithoutIndices.bin')
resource.load()
```

Once the file resource is loaded into memory, its content is accessible via the `data`
property:

```python
print(resource.data)
# b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\x00\x00\...
```

When exporting a model, file resources will be written to disk by default. However,
this can be bypassed by setting the `save_file_resources` flag `False` when calling
`export`:

```python
gltf.export(filename, save_file_resources=False)
```

When creating a model instance manually, if the intention is to also save file
resources, then there must be a corresponding `FileResource` in the `resources`
list for every buffer or image that references a file path (otherwise, an error
will be raised when attempting to export):

```python
resource = FileResource('buffer.bin')
model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=18)])
gltf = GLTF(model=model, resources=[resource])
gltf.export('model.gltf')
```

When instantiating a `FileResource`, if the content of the file is known, it can
be provided via the `data` constructor parameter:

```python
resource = FileResource('buffer.bin', data=b'binary content here')
```

A resource of another type can be converted to a `FileResource` using the
`convert_to_file_resource` helper method on the GLTF class. This method
requires a filename as a parameter, and returns the converted `FileResource`
instance:

```python
resource = gltf.resources[0]
file_resource = gltf.convert_to_file_resource(resource, 'BoxTextured.bin')
```

Note the file will not be created until the model is saved (with `save_file_resources`
flag set to `True`). Also, note that the resource to be converted must be
part of the `resources` list in the model (otherwise an error will be raised).

If the resource is already a `FileResource` and the filename matches, no action
is performed. If the filename is different, then the filename will be updated
on any buffers and images that reference it.

If the resource to be converted is a `GLBResource` or `Base64Resource`, it will be
un-embedded and converted to an external file resource, and any buffers that reference
the resource will be updated appropriately. Any embedded images that reference the
resource will be updated. If the image previously referenced a buffer view, it will
now reference a URI instead; the corresponding buffer view will be removed if no
other parts of the model refer to it. Further, after removing the buffer view, if
no other buffer views refer to the same buffer, then the buffer will be removed as
well.

If the resource to be converted is an `ExternalResource`, this method will raise an
error (accessing external resource data is not supported).

#### Base-64 (Data URI) Resources

glTF supports embedding a resource directly into a JSON-based glTF file (or a GLB
file, though it's not as common) using a
[data URI](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URIs).
In this scenario, the resource is defined as part of the URI itself, allowing the
model to be self-contained without necessarily using the GLB format:

```
{
  ...
  "images": [
    {
      "uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAEDW..."
    }
  ],
  ...
}
```

When loading such a model, a resource of type `Base64Resource` will be instantiated
and added to the model's `resources` list. The `uri` property of the resource will
contain the original data URI, while the `data` property can be used to access the
decoded binary data:

```python
gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF-Embedded/BoxTextured.gltf')
logo = gltf.resources[1]
print(logo.data)
# b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\x00\x00\...
```

To instantiate a `Base64Resource`, there are two options. One is to use the
constructor to pass in the binary data and MIME type (which defaults to
`application/octet-stream` if not provided):

```python
resource = Base64Resource(b'sample binary data', mime_type='application/octet-stream')
```

The other way is to use the `Base64Resource.from_uri` factory method and pass
in the data URI:

```python
resource = Base64Resource.from_uri('data:application/octet-stream;base64,c2FtcGxlIGJpbmFyeSBkYXRh')
```

To convert a resource of another type to a `Base64Resource`, use the
`GLTF.convert_to_base64_resource` helper method. This method accepts an optional
`mime_type` parameter if the MIME type of the original resource is known (defaults
to `application/octet-stream` if not provided):

```python
gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF/BoxTextured.gltf')
logo = gltf.get_resource('CesiumLogoFlat.png')
gltf.convert_to_base64_resource(logo, 'image/png')
gltf.export('BoxTexturedBase64.gltf')
```

If the resource to be converted is already a `Base64Resource`, no action is performed.

If the resource is a `FileResource`, then it will be converted to a `Base64Resource`.
The data for the `FileResource` will be loaded from disk if not already loaded (which
may raise an `IOError` if the file does not exist).

If the resource is a `GLBResource`, it will be converted to a `Base64Resource`. The
GLB buffer will be replaced with a buffer with a data URI (or removed entirely if it
is only used by images). Any images that refer to the resource via a buffer view will
instead refer to the image directly via a data URI, and the corresponding buffer view
will be removed (if it is not also referenced elsewhere). Further, if no other buffer
views refer to the same buffer as the removed buffer view, then the buffer will be
removed entirely as well.

If the resource is an `ExternalResource`, this method will raise an error (accessing
external resource data is not supported).

#### GLB Resources

GLB Resources are resources that are embedded directly in a GLB file as binary
chunks. These resources can only be used with a GLB file (if saving to glTF, these
resources must first be converted to a different type).

There is generally one GLB chunk in a file (with the chunk type `BIN`), though it
is valid to have multiple GLB chunks if they have a different chunk type. This
library supports loading and saving these additional GLB chunks, though no
assumptions are made about their content.

A reference to the `GLBResource` corresponding to the primary GLB chunk (with the
chunk type `BIN`) can be obtained by calling `get_glb_resource` on a model
instance, and its data can be accessed via the `data` property:

```python
gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF-Binary/BoxTextured.glb')
glb_resource = gltf.get_glb_resource()
print(glb_resource.data)
# b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\x00\x00\...
```

Additional GLB chunks can be referenced by calling `get_glb_resource` with a
`resource_type` parameter set to the chunk type:

```python
my_custom_glb_resource = gltf.get_glb_resource(resource_type=123)
```

An individual resource of another type can be converted to a `GLBResource` using
the `embed_resource` helper method. This allows embedding a particular resource
while leaving others external when exporting to GLB (in this scenario, ensure
to use `export_glb` instead of `export`, and set both `embed_buffer_resources`
and `embed_image_resources` to `False` to prevent the other resources from also
being automatically embedded):

```python
gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF-Binary/BoxTextured.glb')
logo = gltf.get_resource('CesiumLogoFlat.png')
gltf.embed_resource(logo)
gltf.export_glb('BoxTexturedPartial.glb', embed_buffer_resources=False, embed_image_resources=False)
```

However, the most common scenario is to embed all resources regardless of their
type, which happens automatically when calling `export` with a `.glb` extension
(or when calling `export_glb` with the default set of parameters).

Note that embedding an `ExternalResource` is not supported because its data is
not accessible (this library does not support loading resources from an external
web URL).

As explained in the other sections, converting a `GLBResource` to a resource of
another type (i.e., "un-embedding" a resource) will typically not only replace
the URIs on the corresponding buffers and images, but may also result in removing
the GLB buffer and buffer views entirely if they are not also referenced elsewhere.

#### External Resources

External resources (represented by the `ExternalResource` class) are resources
that have an external web URL. While this library is able to load models with
external web URLs, the resource itself will not be fetched. A resource of type
`ExternalResource` will be instantiated with the corresponding URI, but the
library will not perform any web requests to load the resource data. Likewise,
the library supports saving a model containing `ExternalResource` instances,
but again, no web requests will be performed.

A resource of another type can be converted to an `ExternalResource` using the
`GLTF.convert_to_external_resource` helper method, which accepts a URL:

```python
gltf = GLTF.load('glTF-Sample-Models/2.0/BoxTextured/glTF/BoxTextured.gltf')
logo = gltf.get_resource('CesiumLogoFlat.png')
gltf.convert_to_external_resource(logo, 'http://www.example.com/image.png')
gltf.export('BoxTexturedExternal.gltf')
```

Again, since this library does not handle calling out to external resources,
this is strictly a bookkeeping operation. It is the responsibility of the caller
to ensure that the resource exists externally. Note when converting a resource
to an `ExternalResource`, the resource data becomes inaccessible.

If the resource is already an `ExternalResource` and the URI matches, no action
is performed. If the URI is different, then the URI will be updated on the resource
instance as well as on any corresponding buffers or images in the model.

If the resource is a `FileResource` or `Base64Resource`, then it will be converted
to an `ExternalResource`, and all buffers and images will be updated appropriately.

If the resource is a `GLBResource`, it will be converted to an `ExternalResource`.
The GLB buffer will be replaced with a buffer with a data URI (or removed entirely
if it is only used by images). Any images that refer to the resource via a buffer
view will instead refer to the image directly via a data URI, and the corresponding
buffer view will be removed (if it is not also referenced elsewhere). Further, if
no other buffer views refer to the same buffer as the removed buffer view, then the
buffer will be removed entirely as well.

## Credits

This project is based on the `pygltflib` library by
[dodgyville](https://gitlab.com/dodgyville) available here:

https://gitlab.com/dodgyville/pygltflib

Specifically, this project is based on a much earlier version of `pygltflib` at a
time when it didn't seem to be actively maintained. I used that library as a
starting point and added some features I needed for my own work. Since then, the
original `pygltflib` project has been revived, but our implementations have
diverged significantly. So now there are two :-)
