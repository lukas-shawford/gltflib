import os
import shutil
import json
from os import path
from unittest import TestCase
from gltflib import (
    GLTF, GLTFModel, Asset, FileResource, ExternalResource, Buffer, BufferView, Image, GLBResource,
    GLB_BINARY_CHUNK_TYPE)


# Temporary directory used for tests
TEMP_DIR = 'tests/temp'

# Directory containing sample files used for tests
SAMPLES_DIR = 'tests/samples'


# Helper function for returning path to a sample file
def sample(filename):
    return path.join(SAMPLES_DIR, filename)


class TestGLTF(TestCase):
    @classmethod
    def setUpClass(cls):
        if path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR)

    def assert_gltf_files_equal(self, filename1, filename2):
        """Helper method for asserting two GLTF files contain equivalent JSON"""
        with open(filename1, 'r') as f1:
            data1 = json.loads(f1.read())
        with open(filename2, 'r') as f2:
            data2 = json.loads(f2.read())
        self.assertDictEqual(data1, data2)

    def test_load(self):
        """Basic test ensuring the class can successfully load a minimal GLTF 2.0 file."""
        # Act
        gltf = GLTF.load(sample('Minimal/minimal.gltf'))

        # Assert
        self.assertIsInstance(gltf, GLTF)
        self.assertEqual(GLTFModel(asset=Asset(version="2.0")), gltf.model)

    def test_export(self):
        """Basic test ensuring the class can successfully save a minimal GLTF 2.0 file."""
        # Arrange
        gltf = GLTF(model=GLTFModel(asset=Asset(version="2.0")))
        filename = path.join(TEMP_DIR, 'minimal.gltf')

        # Act
        gltf.export(filename)

        # Assert
        self.assert_gltf_files_equal(sample('Minimal/minimal.gltf'), filename)

    def test_load_file_resource(self):
        """External files referenced in a glTF model should be loaded as FileResource"""
        # Act
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'))

        # Assert
        self.assertIsInstance(gltf.resources, list)
        resource = gltf.get_resource('triangleWithoutIndices.bin')
        self.assertIsInstance(resource, FileResource)
        self.assertEqual('triangleWithoutIndices.bin', resource.filename)

    def test_load_file_resource_no_autoload(self):
        """File resource contents should not be autoloaded by default"""
        # Act
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'))
        resource = gltf.get_resource('triangleWithoutIndices.bin')

        # Assert
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)
        self.assertIsNone(resource.data)

    def test_load_file_resource_with_autoload(self):
        """When load_file_resources is true, file resource contents should be autoloaded"""
        # Act
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'), load_file_resources=True)
        resource = gltf.get_resource('triangleWithoutIndices.bin')

        # Assert
        self.assertIsInstance(resource, FileResource)
        self.assertTrue(resource.loaded)
        with open(sample('TriangleWithoutIndices/triangleWithoutIndices.bin'), 'rb') as f:
            data = f.read()
        self.assertEqual(data, resource.data)

    def test_load_image_resources(self):
        """Ensure image resources are loaded"""
        # Act
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=True)
        texture = gltf.get_resource('CesiumLogoFlat.png')

        # Assert
        self.assertIsInstance(texture, FileResource)
        with open(sample('BoxTextured/CesiumLogoFlat.png'), 'rb') as f:
            texture_data = f.read()
        self.assertEqual(texture_data, texture.data)

    def test_load_embedded_resources(self):
        """Embedded resources should not be parsed (for now?)"""
        # Act
        gltf = GLTF.load(sample('BoxTexturedEmbedded/BoxTextured.gltf'))

        # Assert
        self.assertEqual(0, len(gltf.resources))

    def test_load_external_resources(self):
        """External resources should be parsed as ExternalResource instances, but otherwise ignored (for now)"""
        # Act
        gltf = GLTF.load(sample('BoxTexturedExternal/BoxTextured.gltf'))
        uri = 'https://www.example.com'
        resource = gltf.get_resource(uri)

        # Assert
        self.assertIsInstance(resource, ExternalResource)
        self.assertEqual(uri, resource.uri)
        # For now, attempting to access the resource data should throw a ValueError
        with self.assertRaises(ValueError):
            _ = resource.data

    def test_load_provided_resources(self):
        """
        Resources that are passed in to the load method should be used if provided (rather than attempting to load
        these resources from the filesystem).
        """
        # Arrange
        data = b'sample binary data'
        resource = FileResource('triangleWithoutIndices.bin', data=data)

        # Act
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'), resources=[resource])
        loaded_resource = gltf.get_resource('triangleWithoutIndices.bin')

        # Assert
        self.assertIs(loaded_resource, resource)
        self.assertEqual(data, loaded_resource.data)
        self.assertIsInstance(loaded_resource, FileResource)
        self.assertTrue(loaded_resource.loaded)

    def test_export_file_resources(self):
        """Test exporting a GLTF model with external file resources"""
        # Arrange
        data = b'sample binary data'
        bytelen = len(data)
        resource = FileResource('buffer.bin', data=data)
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)])
        gltf = GLTF(model=model, resources=[resource])
        filename = path.join(TEMP_DIR, 'sample.gltf')

        # Act
        gltf.export(filename, save_file_resources=True)

        # Assert
        resource_filename = path.join(TEMP_DIR, 'buffer.bin')
        self.assertTrue(path.exists(resource_filename))
        with open(resource_filename, 'rb') as f:
            self.assertEqual(data, f.read())

    def test_skip_exporting_file_resources(self):
        """
        Ensure external file resources are skipped when exporting a GLTF model with save_file_resources set to False
        """
        # Arrange
        resource_filename = path.join(TEMP_DIR, 'buffer.bin')
        if path.exists(resource_filename):
            os.remove(resource_filename)
        data = b'sample binary data'
        bytelen = len(data)
        resource = FileResource('buffer.bin', data=data)
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)])
        gltf = GLTF(model=model, resources=[resource])
        filename = path.join(TEMP_DIR, 'sample.gltf')

        # Act
        gltf.export(filename, save_file_resources=False)

        # Assert
        self.assertFalse(path.exists(resource_filename))

    def test_validate_file_resources_in_buffer_when_exporting(self):
        """
        Test validation for missing external resources referenced in the buffers array when exporting with
        save_file_resources set to True
        """
        # Arrange
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=1024)])
        gltf = GLTF(model=model)
        filename = path.join(TEMP_DIR, 'sample.gltf')

        # Act/Assert
        with self.assertRaisesRegex(RuntimeError, 'Missing resource'):
            gltf.export(filename, save_file_resources=True)

    def test_validate_file_resources_in_image_when_exporting(self):
        """
        Test validation for missing external resources referenced in the images array when exporting with
        save_file_resources set to True
        """
        # Arrange
        model = GLTFModel(asset=Asset(version='2.0'), images=[Image(uri='buffer.bin')])
        gltf = GLTF(model=model)
        filename = path.join(TEMP_DIR, 'sample.gltf')

        # Act/Assert
        with self.assertRaisesRegex(RuntimeError, 'Missing resource'):
            gltf.export(filename, save_file_resources=True)

    def test_load_glb(self):
        """Ensure a model can be loaded from a binary glTF (GLB) file"""
        # Act
        gltf = GLTF.load(sample('Box/glb/Box.glb'))

        # Assert
        self.assertEqual('2.0', gltf.model.asset.version)
        self.assertIsNone(gltf.model.buffers[0].uri)
        self.assertEqual(648, gltf.model.buffers[0].byteLength)
        self.assertEqual(1, len(gltf.resources))
        self.assertEqual(1, len(gltf.glb_resources))
        resource = gltf.resources[0]
        self.assertIsInstance(resource, GLBResource)
        self.assertEqual(648, len(resource.data))

    def test_clone_no_resources(self):
        """Basic test of the clone method for a GLTF model with no resources."""
        # Arrange
        gltf = GLTF(model=GLTFModel(asset=Asset(version="2.0")))

        # Act
        cloned_gltf = gltf.clone()

        # Assert
        # Original and cloned model should be distinct instances
        self.assertIsNot(gltf, cloned_gltf)
        # Model content should be the same
        self.assertEqual(gltf.model, cloned_gltf.model)

    def test_clone_file_resources(self):
        """Cloning a model with file resources should clone both the model and its associated resources."""
        # Arrange
        data = b'sample binary data'
        bytelen = len(data)
        resource = FileResource('buffer.bin', data=data)
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)])
        gltf = GLTF(model=model, resources=[resource])

        # Act
        cloned_gltf = gltf.clone()

        # Assert
        # Original and cloned model should be distinct instances
        self.assertIsNot(gltf, cloned_gltf)
        # Model content should be the same
        self.assertEqual(gltf.model, cloned_gltf.model)
        # Resource list should be cloned
        self.assertIsNot(gltf.resources, cloned_gltf.resources)
        # Resource list should still contain one FileResource
        self.assertEqual(1, len(cloned_gltf.resources))
        cloned_file_resource = cloned_gltf.resources[0]
        self.assertIsInstance(cloned_file_resource, FileResource)
        # FileResource should be cloned
        self.assertIsNot(cloned_file_resource, resource)
        # Since the original file resource was loaded, the cloned file resource should be loaded as well
        self.assertTrue(cloned_file_resource.loaded)
        # Resource uri and data should be the same
        self.assertEqual(resource.uri, cloned_file_resource.uri)
        self.assertEqual(resource.data, cloned_file_resource.data)

    def test_cloned_file_resources_remains_not_loaded_if_original_was_not_loaded(self):
        """
        When cloning a model with a FileResource that was not explicitly loaded, the cloned FileResource should also
        remain not loaded.
        """
        # Arrange
        # Load a glTF model with load_file_resources set to False
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=False)
        # Resource should initially not be loaded
        resource = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)

        # Act
        cloned_gltf = gltf.clone()

        # Assert
        # Original and cloned model should be distinct instances
        self.assertIsNot(gltf, cloned_gltf)
        # Model content should be the same
        self.assertEqual(gltf.model, cloned_gltf.model)
        # Resource list should be cloned
        self.assertIsNot(gltf.resources, cloned_gltf.resources)
        # Resource list should contain two FileResources
        self.assertEqual(2, len(cloned_gltf.resources))
        cloned_file_resource = cloned_gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(cloned_file_resource, FileResource)
        # FileResource should be cloned
        self.assertIsNot(cloned_file_resource, resource)
        # Since the original file resource was not loaded, the cloned file resource should also remain not loaded
        self.assertFalse(cloned_file_resource.loaded)
        # Cloned resource uri should be the same
        self.assertEqual('CesiumLogoFlat.png', cloned_file_resource.uri)
        # Resource data should be None since it was not loaded
        self.assertIsNone(cloned_file_resource.data)

    def test_clone_model_with_glb_resource(self):
        """Cloning a model with a GLB resource should clone both the model and its associated resources."""
        # Arrange
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(byteLength=4)])
        resource = GLBResource(b'data')
        gltf = GLTF(model=model, resources=[resource])

        # Act
        cloned_gltf = gltf.clone()

        # Assert
        # Resource list should still contain one GLBResource
        self.assertEqual(1, len(cloned_gltf.resources))
        cloned_glb_resource = cloned_gltf.resources[0]
        self.assertIsInstance(cloned_glb_resource, GLBResource)
        # GLBResource should be cloned
        self.assertIsNot(cloned_glb_resource, resource)
        # GLBResource uri should be None
        self.assertIsNone(cloned_glb_resource.uri)
        # Resource data should be the same
        self.assertEqual(resource.data, cloned_glb_resource.data)

    def test_embed_file_resource(self):
        """Test embedding a file resource"""
        # Arrange
        data = b'sample binary data'
        bytelen = len(data)
        model = GLTFModel(
            asset=Asset(version='2.0'),
            buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)],
            bufferViews=[BufferView(buffer=0, byteOffset=0, byteLength=18)]
        )
        file_resource = FileResource(filename='buffer.bin', data=data)
        gltf = GLTF(model=model, resources=[file_resource])

        # Act
        glb_resource = gltf.embed_resource(file_resource)

        # Assert
        # Model should now contain a single GLB resource
        self.assertEqual([glb_resource], gltf.resources)
        # Resource data should be null-padded to a multiple of 4 bytes
        self.assertEqual(b'sample binary data\x00\x00', glb_resource.data)
        # Original file resource should not be mutated
        self.assertEqual(b'sample binary data', file_resource.data)
        # Buffer URI should now be undefined since it is embedded, and byte length should be padded to a multiple of 4
        self.assertEqual([Buffer(byteLength=20)], model.buffers)
        # Buffer view should not be modified in this case
        self.assertEqual([BufferView(buffer=0, byteOffset=0, byteLength=18)], model.bufferViews)

    def test_embed_glb_resource_does_nothing(self):
        """Ensure that calling embed_resource on a GLBResource does nothing (since it is already embedded)"""
        # Arrange
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(byteLength=4)])
        resource = GLBResource(b'data')
        gltf = GLTF(model=model, resources=[resource])

        # Act
        glb_resource = gltf.embed_resource(resource)

        # Assert
        self.assertIs(glb_resource, resource)
        self.assertEqual([Buffer(byteLength=4)], model.buffers)

    def test_embed_file_resource_with_existing_glb_resources(self):
        """Ensure that embedding a file resource works correctly when the model already has existing GLB resources."""
        # Arrange
        # Existing GLB resource
        glb_resource_data = b'some data'
        glb_resource_bytelen = len(glb_resource_data)
        glb_resource = GLBResource(glb_resource_data)
        # Another GLB resource with a custom resource type
        custom_glb_resource_data = b'more data'
        custom_glb_resource = GLBResource(custom_glb_resource_data, resource_type=123)
        # Sample buffer 1 data (to be embedded)
        buffer_1_filename = 'buffer_1.bin'
        buffer_1_data = b'sample buffer one data'
        buffer_1_bytelen = len(buffer_1_data)
        # Sample buffer 2 data (to remain external)
        buffer_2_filename = 'buffer_2.bin'
        buffer_2_data = b'sample buffer two data'
        buffer_2_bytelen = len(buffer_2_data)
        # Sample image data (to be embedded)
        image_filename = 'image.png'
        image_data = b'sample image data'
        image_bytelen = len(image_data)
        # File Resources
        file_resource_1 = FileResource(filename=buffer_1_filename, data=buffer_1_data)
        file_resource_2 = FileResource(filename=buffer_2_filename, data=buffer_2_data)
        file_resource_3 = FileResource(filename=image_filename, data=image_data, mimetype='image/jpeg')
        # Create GLTF Model
        model = GLTFModel(asset=Asset(version='2.0'),
                          buffers=[
                              Buffer(byteLength=glb_resource_bytelen),
                              Buffer(uri=buffer_1_filename, byteLength=buffer_1_bytelen),
                              Buffer(uri=buffer_2_filename, byteLength=buffer_2_bytelen)
                          ],
                          bufferViews=[
                              BufferView(buffer=0, byteOffset=0, byteLength=5),
                              BufferView(buffer=0, byteOffset=5, byteLength=4),
                              BufferView(buffer=1, byteOffset=0, byteLength=10),
                              BufferView(buffer=1, byteOffset=10, byteLength=12),
                              BufferView(buffer=2, byteOffset=0, byteLength=10),
                              BufferView(buffer=2, byteOffset=10, byteLength=12)
                          ],
                          images=[Image(uri=image_filename)])
        gltf = GLTF(model=model, resources=[
            glb_resource,
            custom_glb_resource,
            file_resource_1,
            file_resource_2,
            file_resource_3
        ])

        # Act
        gltf.embed_resource(file_resource_1)
        gltf.embed_resource(file_resource_3)

        # Assert
        # There should now be 3 resources total (existing GLB resource, the custom GLB resource, and file_resource_2
        # which was not embedded)
        self.assertEqual(3, len(gltf.resources))
        # Ensure the existing GLB resource is still present
        self.assertIs(glb_resource, gltf.get_glb_resource())
        # Existing GLB resource should have its original data together with the data from file_resource_1 and
        # file_resource_3 (each block null-padded to 4 byte intervals).
        self.assertEqual(b'some data\x00\x00\x00sample buffer one data\x00\x00sample image data\x00\x00\x00',
                         glb_resource.data)
        # The custom GLB resource should still be present and not mutated in any way
        self.assertIs(custom_glb_resource, gltf.get_glb_resource(123))
        self.assertEqual(b'more data', custom_glb_resource.data)
        # file_resource_2 should remain external with its data intact
        self.assertIs(file_resource_2, gltf.get_resource(buffer_2_filename))
        self.assertEqual(b'sample buffer two data', file_resource_2.data)
        # First buffer (referring to the embedded GLB buffer) should be expanded, and its URI should remain undefined
        self.assertIsNone(model.buffers[0].uri)
        self.assertEqual(56, model.buffers[0].byteLength)
        # Second buffer should remain in the model and have its original data intact since it was not embedded
        self.assertEqual(Buffer(uri=buffer_2_filename, byteLength=buffer_2_bytelen), model.buffers[1])
        # There should be two buffers total
        self.assertEqual(2, len(model.buffers))
        # Ensure buffer view contents match what is expected. The offsets and byte lengths are adjusted to point to the
        # embedded data. There should be a new buffer view for the embedded image
        self.assertEqual([
            BufferView(buffer=0, byteOffset=0, byteLength=5),
            BufferView(buffer=0, byteOffset=5, byteLength=4),
            BufferView(buffer=0, byteOffset=12, byteLength=10),
            BufferView(buffer=0, byteOffset=22, byteLength=12),
            BufferView(buffer=1, byteOffset=0, byteLength=10),
            BufferView(buffer=1, byteOffset=10, byteLength=12),
            BufferView(buffer=0, byteOffset=36, byteLength=image_bytelen)
        ], model.bufferViews)
        # Embedded image should now point to a buffer view instead
        self.assertEqual([Image(uri=image_filename, bufferView=6)], model.images)

    def test_embed_missing_resource_raises_error(self):
        """Attempting to embed a resource that is not present in the resources list should raise a ValueError"""
        # Arrange
        file_resource = FileResource(filename='buffer.bin', data=b'sample binary data')
        gltf = GLTF(model=GLTFModel(asset=Asset(version='2.0')))

        # Act/Assert
        with self.assertRaises(ValueError):
            gltf.embed_resource(file_resource)

    def test_embed_external_resource_raises_error(self):
        """Attempting to embed an ExternalResource should raise a ValueError (not yet supported)"""
        # Arrange
        resource = ExternalResource(uri='http://www.example.com/')
        gltf = GLTF(model=GLTFModel(asset=Asset(version='2.0')), resources=[resource])

        # Act/Assert
        with self.assertRaises(TypeError):
            gltf.embed_resource(resource)

    def test_export_glb(self):
        """Basic test to ensure a model can be saved in GLB format"""
        # Arrange
        data = b'sample binary data'
        bytelen = len(data)
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)])
        file_resource = FileResource(filename='buffer.bin', data=data)
        gltf = GLTF(model=model, resources=[file_resource])

        # Act
        filename = path.join(TEMP_DIR, 'sample.glb')
        gltf2 = gltf.export(filename)

        # Assert
        # Resources on the original model instance should not be mutated
        self.assertEqual([file_resource], gltf.resources)
        self.assertEqual(data, file_resource.data)
        # Exported model should contain a single GLB resource
        self.assertEqual(1, len(gltf2.resources))
        self.assertIsInstance(gltf2.resources[0], GLBResource)
        # Read the exported file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        self.assertEqual(1, len(glb.model.buffers))
        buffer = glb.model.buffers[0]
        self.assertIsInstance(buffer, Buffer)
        # Buffer URI should be undefined since the data is now embedded
        self.assertIsNone(buffer.uri)
        # Binary data should be padded to a multiple of 4
        self.assertEqual(20, buffer.byteLength)
        # Original model instance should retain its buffer with the original uri
        self.assertEqual([Buffer(uri='buffer.bin', byteLength=bytelen)], gltf.model.buffers)
        # Ensure embedded GLB resource was parsed correctly
        self.assertEqual(1, len(glb.resources))
        resource = glb.get_glb_resource()
        self.assertIsInstance(resource, GLBResource)
        # Binary data should be null-padded so its length is a multiple of 4 bytes
        self.assertEqual(b'sample binary data\x00\x00', resource.data)
        # Original resource data should not be mutated
        self.assertEqual(b'sample binary data', file_resource.data)

    def test_export_glb_multiple_buffers(self):
        """
        Ensures that a model with multiple buffers and buffer views is exported correctly as GLB. The buffers should be
        merged into a single buffer, and all buffer views that reference the buffer should have their byte offsets
        adjusted.
        """
        # Arrange
        data1 = b'sample binary data'
        bytelen1 = len(data1)
        data2 = b'some more binary data'
        bytelen2 = len(data2)
        file_resource_1 = FileResource(filename='buffer1.bin', data=data1)
        file_resource_2 = FileResource(filename='buffer2.bin', data=data2)
        model = GLTFModel(
            asset=Asset(version='2.0'),
            buffers=[
                Buffer(uri='buffer1.bin', byteLength=bytelen1),
                Buffer(uri='buffer2.bin', byteLength=bytelen2)
            ],
            bufferViews=[
                BufferView(buffer=0, byteOffset=0, byteLength=10),
                BufferView(buffer=0, byteOffset=10, byteLength=8),
                BufferView(buffer=1, byteOffset=0, byteLength=21)
            ]
        )
        gltf = GLTF(model=model, resources=[
            file_resource_1,
            file_resource_2
        ])

        # Act
        filename = path.join(TEMP_DIR, 'sample2.glb')
        gltf2 = gltf.export(filename)

        # Assert
        # Resources on the original model instance should not be mutated
        self.assertEqual([file_resource_1, file_resource_2], gltf.resources)
        self.assertEqual(data1, file_resource_1.data)
        self.assertEqual(data2, file_resource_2.data)
        # The exported model should contain a single GLB resource
        self.assertEqual(1, len(gltf2.resources))
        self.assertIsInstance(gltf2.resources[0], GLBResource)
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        # The two buffers should be merged into one
        self.assertEqual(1, len(glb.model.buffers))
        # Buffer URI should be undefined since the data is now embedded
        buffer = glb.model.buffers[0]
        self.assertIsNone(buffer.uri)
        # Original model instance should retain its original buffers and buffer views
        self.assertEqual([
            Buffer(uri='buffer1.bin', byteLength=bytelen1),
            Buffer(uri='buffer2.bin', byteLength=bytelen2)
        ], gltf.model.buffers)
        self.assertEqual([
            BufferView(buffer=0, byteOffset=0, byteLength=10),
            BufferView(buffer=0, byteOffset=10, byteLength=8),
            BufferView(buffer=1, byteOffset=0, byteLength=21)
        ], gltf.model.bufferViews)
        # Ensure embedded GLB resource was parsed correctly
        self.assertEqual(1, len(glb.resources))
        resource = glb.get_glb_resource()
        self.assertIsInstance(resource, GLBResource)
        # Binary data should be merged and its individual chunks null-padded so that they align to a 4-byte boundary
        self.assertEqual(b'sample binary data\x00\x00some more binary data\x00\x00\x00', resource.data)
        self.assertEqual(44, buffer.byteLength)
        # Buffer views should now point to the GLB buffer (index 0) and have their offsets adjusted based on the
        # merged data.
        self.assertEqual(BufferView(buffer=0, byteOffset=0, byteLength=10), glb.model.bufferViews[0])
        self.assertEqual(BufferView(buffer=0, byteOffset=10, byteLength=8), glb.model.bufferViews[1])
        self.assertEqual(BufferView(buffer=0, byteOffset=20, byteLength=21), glb.model.bufferViews[2])

    def test_export_glb_embed_image(self):
        """Tests embedding an image into the GLB that was previously an external file reference"""
        # Arrange
        data = b'sample image data'
        bytelen = len(data)
        image_filename = 'image.png'
        model = GLTFModel(asset=Asset(version='2.0'), images=[Image(uri=image_filename)])
        gltf = GLTF(model=model, resources=[FileResource(filename=image_filename, data=data, mimetype='image/jpeg')])

        # Act
        filename = path.join(TEMP_DIR, 'sample3.glb')
        gltf.export(filename)

        # Assert
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        self.assertEqual(1, len(glb.model.buffers))
        buffer = glb.model.buffers[0]
        self.assertIsInstance(buffer, Buffer)
        # Buffer URI should be undefined since the data is now embedded
        self.assertIsNone(buffer.uri)
        # Binary data should be padded to a multiple of 4
        self.assertEqual(20, buffer.byteLength)
        # Ensure embedded GLB resource was parsed correctly
        self.assertEqual(1, len(glb.resources))
        resource = glb.get_glb_resource()
        self.assertIsInstance(resource, GLBResource)
        # Binary data should be null-padded so its length is a multiple of 4 bytes
        self.assertEqual(b'sample image data\x00\x00\x00', resource.data)
        # Ensure image was transformed so it points to a buffer view
        image = glb.model.images[0]
        self.assertIsInstance(image, Image)
        self.assertEqual(0, image.bufferView)
        # Original image URI should still be retained (if bufferView is defined, it is used instead of uri)
        self.assertEqual(image_filename, image.uri)
        # MIME type is required if image is stored in a buffer. Ensure it got stored correctly based on what we
        # passed in via the FileResource (even if it's not technically the correct MIME type for a PNG image).
        self.assertEqual('image/jpeg', image.mimeType)
        # Ensure that a buffer view was created for the embedded image
        self.assertEqual(1, len(glb.model.bufferViews))
        buffer_view = glb.model.bufferViews[0]
        self.assertIsInstance(buffer_view, BufferView)
        # Ensure buffer view has the correct information
        self.assertEqual(0, buffer_view.buffer)
        self.assertEqual(0, buffer_view.byteOffset)
        self.assertEqual(bytelen, buffer_view.byteLength)

    def test_export_glb_mixed_resources(self):
        """Tests embedding both buffer and image resources into a GLB"""
        # Arrange
        # Sample buffer 1 data
        buffer_1_filename = 'buffer_1.bin'
        buffer_1_data = b'sample buffer one data'
        buffer_1_bytelen = len(buffer_1_data)
        # Sample buffer 2 data
        buffer_2_filename = 'buffer_2.bin'
        buffer_2_data = b'sample buffer two data'
        buffer_2_bytelen = len(buffer_2_data)
        # Sample image data
        image_filename = 'image.png'
        image_data = b'sample image data'
        image_bytelen = len(image_data)
        # File Resources
        file_resource_1 = FileResource(filename=buffer_1_filename, data=buffer_1_data)
        file_resource_2 = FileResource(filename=buffer_2_filename, data=buffer_2_data)
        file_resource_3 = FileResource(filename=image_filename, data=image_data, mimetype='image/jpeg')
        # Create GLTF Model
        model = GLTFModel(asset=Asset(version='2.0'),
                          buffers=[
                              Buffer(uri=buffer_1_filename, byteLength=buffer_1_bytelen),
                              Buffer(uri=buffer_2_filename, byteLength=buffer_2_bytelen)
                          ],
                          bufferViews=[
                              BufferView(buffer=0, byteOffset=0, byteLength=10),
                              BufferView(buffer=0, byteOffset=10, byteLength=12),
                              BufferView(buffer=1, byteOffset=0, byteLength=10),
                              BufferView(buffer=1, byteOffset=10, byteLength=12)
                          ],
                          images=[Image(uri=image_filename)])
        gltf = GLTF(model=model, resources=[
            file_resource_1,
            file_resource_2,
            file_resource_3
        ])

        # Act
        filename = path.join(TEMP_DIR, 'sample4.glb')
        gltf2 = gltf.export(filename)

        # Assert
        # Resources on the original model instance should not be mutated
        self.assertEqual([file_resource_1, file_resource_2, file_resource_3], gltf.resources)
        self.assertEqual(buffer_1_data, file_resource_1.data)
        self.assertEqual(buffer_2_data, file_resource_2.data)
        self.assertEqual(image_data, file_resource_3.data)
        # The exported model should contain a single GLB resource
        self.assertEqual(1, len(gltf2.resources))
        self.assertIsInstance(gltf2.resources[0], GLBResource)
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        self.assertEqual(1, len(glb.model.buffers))
        buffer = glb.model.buffers[0]
        self.assertIsInstance(buffer, Buffer)
        # Buffer URI should be undefined since the data is now embedded
        self.assertIsNone(buffer.uri)
        # Original model instance should retain its original buffers, buffer views, and images
        self.assertEqual([
            Buffer(uri=buffer_1_filename, byteLength=buffer_1_bytelen),
            Buffer(uri=buffer_2_filename, byteLength=buffer_2_bytelen)
        ], gltf.model.buffers)
        self.assertEqual([
            BufferView(buffer=0, byteOffset=0, byteLength=10),
            BufferView(buffer=0, byteOffset=10, byteLength=12),
            BufferView(buffer=1, byteOffset=0, byteLength=10),
            BufferView(buffer=1, byteOffset=10, byteLength=12)
        ], gltf.model.bufferViews)
        self.assertEqual([Image(uri=image_filename)], gltf.model.images)
        # Ensure embedded GLB resource was parsed correctly
        self.assertEqual(1, len(glb.resources))
        resource = glb.get_glb_resource()
        self.assertIsInstance(resource, GLBResource)
        # Binary data should be merged and its individual chunks null-padded so that they align to a 4-byte boundary
        self.assertEqual(b'sample buffer one data\x00\x00sample buffer two data\x00\x00sample image data\x00\x00\x00',
                         resource.data)
        self.assertEqual(68, buffer.byteLength)
        # Buffer views should now point to the GLB buffer (index 0) and have their offsets adjusted based on the
        # merged data.
        self.assertEqual(BufferView(buffer=0, byteOffset=0, byteLength=10), glb.model.bufferViews[0])
        self.assertEqual(BufferView(buffer=0, byteOffset=10, byteLength=12), glb.model.bufferViews[1])
        self.assertEqual(BufferView(buffer=0, byteOffset=24, byteLength=10), glb.model.bufferViews[2])
        self.assertEqual(BufferView(buffer=0, byteOffset=34, byteLength=12), glb.model.bufferViews[3])
        # Ensure a buffer view was added for the embedded image
        self.assertEqual(5, len(glb.model.bufferViews))
        # Ensure the image buffer view has the correct byte length and offset
        image_buffer_view = glb.model.bufferViews[4]
        self.assertIsInstance(image_buffer_view, BufferView)
        self.assertEqual(0, image_buffer_view.buffer)
        self.assertEqual(48, image_buffer_view.byteOffset)
        self.assertEqual(image_bytelen, image_buffer_view.byteLength)
        # Ensure image was transformed so it points to a buffer view
        image = glb.model.images[0]
        self.assertIsInstance(image, Image)
        self.assertEqual(4, image.bufferView)
        # Image URI should be retained (if bufferView is defined, it is used instead of uri)
        self.assertEqual(image_filename, image.uri)

    def test_export_glb_with_embedded_image(self):
        """
        Tests exporting a model to GLB that already contains an embedded image, and a FileResource to be newly embedded.
        """
        # Arrange
        # Sample buffer 1 data (to be embedded)
        buffer_1_filename = 'buffer_1.bin'
        buffer_1_data = b'sample buffer one data'
        buffer_1_bytelen = len(buffer_1_data)
        # Sample image data (already embedded)
        image_filename = 'image.png'
        image_data = b'sample image data'
        image_bytelen = len(image_data)
        # Create resources
        glb_resource = GLBResource(data=image_data)
        file_resource = FileResource(filename=buffer_1_filename, data=buffer_1_data)
        # Create GLTF Model
        model = GLTFModel(asset=Asset(version='2.0'),
                          buffers=[
                              Buffer(byteLength=image_bytelen),
                              Buffer(uri=buffer_1_filename, byteLength=buffer_1_bytelen)
                          ],
                          bufferViews=[
                              BufferView(buffer=0, byteOffset=0, byteLength=image_bytelen),
                              BufferView(buffer=1, byteOffset=0, byteLength=buffer_1_bytelen)
                          ],
                          images=[Image(uri=image_filename, bufferView=0)])
        gltf = GLTF(model=model, resources=[glb_resource, file_resource])

        # Act
        filename = path.join(TEMP_DIR, 'sample5.glb')
        gltf2 = gltf.export(filename)

        # Assert
        # Resources on the original model instance should not be mutated
        self.assertEqual([glb_resource, file_resource], gltf.resources)
        self.assertEqual(b'sample image data', glb_resource.data)
        self.assertEqual(b'sample buffer one data', file_resource.data)
        # The exported model should contain a single GLB resource
        self.assertEqual(1, len(gltf2.resources))
        self.assertIsInstance(gltf2.resources[0], GLBResource)
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        self.assertEqual(1, len(glb.model.buffers))
        buffer = glb.model.buffers[0]
        self.assertIsInstance(buffer, Buffer)
        # Buffer URI should be undefined since the data is now embedded
        self.assertIsNone(buffer.uri)
        # Original model instance should retain its original buffers, buffer views, and images
        self.assertEqual([
            Buffer(byteLength=image_bytelen),
            Buffer(uri=buffer_1_filename, byteLength=buffer_1_bytelen)
        ], gltf.model.buffers)
        self.assertEqual([
            BufferView(buffer=0, byteOffset=0, byteLength=image_bytelen),
            BufferView(buffer=1, byteOffset=0, byteLength=buffer_1_bytelen)
        ], gltf.model.bufferViews)
        self.assertEqual([Image(uri=image_filename, bufferView=0)], gltf.model.images)
        # Ensure embedded GLB resource was parsed correctly
        self.assertEqual(1, len(glb.resources))
        resource = glb.get_glb_resource()
        self.assertIsInstance(resource, GLBResource)
        # Binary data should be merged and its individual chunks null-padded so that they align to a 4-byte boundary
        self.assertEqual(b'sample image data\x00\x00\x00sample buffer one data\x00\x00', resource.data)
        self.assertEqual(44, buffer.byteLength)
        # Buffer views should now point to the GLB buffer (index 0) and have their offsets adjusted based on the
        # merged data.
        self.assertEqual(2, len(glb.model.bufferViews))
        self.assertEqual(BufferView(buffer=0, byteOffset=0, byteLength=17), glb.model.bufferViews[0])
        self.assertEqual(BufferView(buffer=0, byteOffset=20, byteLength=22), glb.model.bufferViews[1])

    def test_export_glb_with_existing_glb_buffer_and_resource(self):
        """
        Ensure that when exporting a GLB model with an existing GLBResource and a GLB buffer works correctly (existing
        buffer and resource should be preserved, and no new ones added)
        """
        # Arrange
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(byteLength=4)])
        resource = GLBResource(b'data')
        gltf = GLTF(model=model, resources=[resource])

        # Act
        filename = path.join(TEMP_DIR, 'sample6.glb')
        gltf.export(filename)

        # Assert
        # Load back the GLB and ensure it has the correct structure
        glb = GLTF.load(filename)
        self.assertEqual(1, len(glb.model.buffers))
        buffer = glb.model.buffers[0]
        self.assertIsInstance(buffer, Buffer)
        self.assertIsNone(buffer.uri)
        self.assertEqual(4, buffer.byteLength)
        # Validate GLB resource remains as is
        self.assertEqual(1, len(glb.resources))
        glb_resource = glb.get_glb_resource()
        self.assertIsInstance(glb_resource, GLBResource)
        self.assertEqual(b'data', glb_resource.data)

    def test_export_glb_with_external_image_resource(self):
        """
        Tests exporting a binary GLB file with image resources remaining external.
        """
        # Arrange
        # Sample buffer 1 data
        buffer_1_filename = 'buffer_1.bin'
        buffer_1_data = b'sample buffer one data'
        buffer_1_bytelen = len(buffer_1_data)
        # Sample buffer 2 data
        buffer_2_filename = 'buffer_2.bin'
        buffer_2_data = b'sample buffer two data'
        buffer_2_bytelen = len(buffer_2_data)
        # Sample image data (this will remain external)
        image_filename = 'sample7.png'
        image_data = b'sample image data'
        # Create GLTF Model
        model = GLTFModel(asset=Asset(version='2.0'),
                          buffers=[
                              Buffer(uri=buffer_1_filename, byteLength=buffer_1_bytelen),
                              Buffer(uri=buffer_2_filename, byteLength=buffer_2_bytelen)
                          ],
                          bufferViews=[
                              BufferView(buffer=0, byteOffset=0, byteLength=10),
                              BufferView(buffer=0, byteOffset=10, byteLength=12),
                              BufferView(buffer=1, byteOffset=0, byteLength=10),
                              BufferView(buffer=1, byteOffset=10, byteLength=12)
                          ],
                          images=[Image(uri=image_filename)])
        gltf = GLTF(model=model, resources=[
            FileResource(filename=buffer_1_filename, data=buffer_1_data),
            FileResource(filename=buffer_2_filename, data=buffer_2_data),
            FileResource(filename=image_filename, data=image_data, mimetype='image/jpeg')
        ])

        # Act
        # Export the GLB (do not embed image resources)
        filename = path.join(TEMP_DIR, 'sample7.glb')
        gltf.export_glb(filename, embed_image_resources=False)

        # Assert
        # Ensure the image got saved
        self.assertTrue(path.exists(path.join(TEMP_DIR, image_filename)))
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename, load_file_resources=True)
        self.assertEqual(model.asset, glb.model.asset)
        self.assertEqual(1, len(glb.model.buffers))
        buffer = glb.model.buffers[0]
        self.assertIsInstance(buffer, Buffer)
        # Buffer URI should be undefined since the data is now embedded
        self.assertIsNone(buffer.uri)
        # Ensure there are two resources since the image should remain external
        self.assertEqual(2, len(glb.resources))
        # Ensure embedded GLB resource was parsed correctly
        resource = glb.get_glb_resource()
        self.assertIsInstance(resource, GLBResource)
        # Binary data should be merged and its individual chunks null-padded so that they align to a 4-byte boundary
        self.assertEqual(b'sample buffer one data\x00\x00sample buffer two data\x00\x00',
                         resource.data)
        self.assertEqual(48, buffer.byteLength)
        # Buffer views should now point to the GLB buffer (index 0) and have their offsets adjusted based on the
        # merged data.
        self.assertEqual(BufferView(buffer=0, byteOffset=0, byteLength=10), glb.model.bufferViews[0])
        self.assertEqual(BufferView(buffer=0, byteOffset=10, byteLength=12), glb.model.bufferViews[1])
        self.assertEqual(BufferView(buffer=0, byteOffset=24, byteLength=10), glb.model.bufferViews[2])
        self.assertEqual(BufferView(buffer=0, byteOffset=34, byteLength=12), glb.model.bufferViews[3])
        # Ensure there are still 4 buffer views (rather than 5 if the image was embedded)
        self.assertEqual(4, len(glb.model.bufferViews))
        # Ensure the image resource remains external
        image_resource = glb.get_resource(image_filename)
        self.assertIsInstance(image_resource, FileResource)
        # Ensure image filename and data are retained after export
        self.assertEqual(image_filename, image_resource.filename)
        self.assertEqual(b'sample image data', image_resource.data)
        # Ensure image is retained in the model structure
        image = glb.model.images[0]
        self.assertIsInstance(image, Image)
        self.assertEqual(image_filename, image.uri)

    def test_export_glb_with_all_resources_remaining_external(self):
        """
        Tests exporting a binary GLB file with all resources (buffer and image) remaining external.
        """
        # Arrange
        # Sample buffer 1 data (this will remain external)
        buffer_1_filename = 'sample_8_buffer_1.bin'
        buffer_1_data = b'sample buffer one data'
        buffer_1_bytelen = len(buffer_1_data)
        # Sample buffer 2 data (this will remain external)
        buffer_2_filename = 'sample_8_buffer_2.bin'
        buffer_2_data = b'sample buffer two data'
        buffer_2_bytelen = len(buffer_2_data)
        # Sample image data (this will remain external)
        image_filename = 'sample_8_image.png'
        image_data = b'sample image data'
        # Create GLTF Model
        model = GLTFModel(asset=Asset(version='2.0'),
                          buffers=[
                              Buffer(uri=buffer_1_filename, byteLength=buffer_1_bytelen),
                              Buffer(uri=buffer_2_filename, byteLength=buffer_2_bytelen)
                          ],
                          bufferViews=[
                              BufferView(buffer=0, byteOffset=0, byteLength=10),
                              BufferView(buffer=0, byteOffset=10, byteLength=12),
                              BufferView(buffer=1, byteOffset=0, byteLength=10),
                              BufferView(buffer=1, byteOffset=10, byteLength=12)
                          ],
                          images=[Image(uri=image_filename)])
        gltf = GLTF(model=model, resources=[
            FileResource(filename=buffer_1_filename, data=buffer_1_data),
            FileResource(filename=buffer_2_filename, data=buffer_2_data),
            FileResource(filename=image_filename, data=image_data, mimetype='image/jpeg')
        ])

        # Act
        # Export the GLB (do not embed buffer or image resources)
        filename = path.join(TEMP_DIR, 'sample8.glb')
        gltf.export_glb(filename, embed_buffer_resources=False, embed_image_resources=False)

        # Assert
        # Ensure the buffer and image files got saved
        self.assertTrue(path.exists(path.join(TEMP_DIR, buffer_1_filename)))
        self.assertTrue(path.exists(path.join(TEMP_DIR, buffer_2_filename)))
        self.assertTrue(path.exists(path.join(TEMP_DIR, image_filename)))
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename, load_file_resources=True)
        self.assertEqual(model.asset, glb.model.asset)
        # Ensure there are still 2 buffers (they should not get merged)
        self.assertEqual(2, len(glb.model.buffers))
        buffer1 = glb.model.buffers[0]
        self.assertIsInstance(buffer1, Buffer)
        buffer2 = glb.model.buffers[1]
        self.assertIsInstance(buffer2, Buffer)
        # Ensure buffer URIs and byte lengths are retained
        self.assertEqual(buffer_1_filename, buffer1.uri)
        self.assertEqual(buffer_1_bytelen, buffer1.byteLength)
        self.assertEqual(buffer_2_filename, buffer2.uri)
        self.assertEqual(buffer_2_bytelen, buffer2.byteLength)
        # Ensure there are three resources since all resources should remain external
        self.assertEqual(3, len(glb.resources))
        # Ensure there is no embedded GLB resource
        self.assertIsNone(glb.get_glb_resource())
        # Ensure buffer views are retained with their original byte offsets and byte lengths
        self.assertEqual(BufferView(buffer=0, byteOffset=0, byteLength=10), glb.model.bufferViews[0])
        self.assertEqual(BufferView(buffer=0, byteOffset=10, byteLength=12), glb.model.bufferViews[1])
        self.assertEqual(BufferView(buffer=1, byteOffset=0, byteLength=10), glb.model.bufferViews[2])
        self.assertEqual(BufferView(buffer=1, byteOffset=10, byteLength=12), glb.model.bufferViews[3])
        # Ensure there are still 4 buffer views (rather than 5 if the image was embedded)
        self.assertEqual(4, len(glb.model.bufferViews))
        # Ensure the buffer resources are parsed correctly and can be referenced by URI
        buffer_1_resource = glb.get_resource(buffer_1_filename)
        self.assertIsInstance(buffer_1_resource, FileResource)
        self.assertEqual(buffer_1_filename, buffer_1_resource.filename)
        buffer_2_resource = glb.get_resource(buffer_2_filename)
        self.assertIsInstance(buffer_2_resource, FileResource)
        self.assertEqual(buffer_2_filename, buffer_2_resource.filename)
        # Ensure the image resource remains external
        image_resource = glb.get_resource(image_filename)
        self.assertIsInstance(image_resource, FileResource)
        # Ensure image filename and data are retained after export
        self.assertEqual(image_filename, image_resource.filename)
        self.assertEqual(b'sample image data', image_resource.data)
        # Ensure image is retained in the model structure
        image = glb.model.images[0]
        self.assertIsInstance(image, Image)
        self.assertEqual(image_filename, image.uri)

    def test_export_glb_with_external_image_resource_skip_saving_files(self):
        """
        When exporting a binary GLB with some resources remaining external, test that we can skip actually saving these
        external resources by setting the save_file_resources to False during export.
        """
        # Arrange
        # Sample buffer data
        buffer_filename = 'buffer.bin'
        buffer_data = b'sample buffer one data'
        buffer_bytelen = len(buffer_data)
        # Sample image data (this will remain external, and we will skip actually saving it)
        image_filename = 'sample9.png'
        image_data = b'sample image data'
        # Create GLTF Model
        model = GLTFModel(asset=Asset(version='2.0'),
                          buffers=[Buffer(uri=buffer_filename, byteLength=buffer_bytelen)],
                          bufferViews=[BufferView(buffer=0, byteOffset=0, byteLength=22)],
                          images=[Image(uri=image_filename)])
        gltf = GLTF(model=model, resources=[
            FileResource(filename=buffer_filename, data=buffer_data),
            FileResource(filename=image_filename, data=image_data, mimetype='image/jpeg')
        ])

        # Act
        # Export the GLB (do not embed image resources, and skip saving file resources)
        filename = path.join(TEMP_DIR, 'sample9.glb')
        gltf.export_glb(filename, embed_image_resources=False, save_file_resources=False)

        # Assert
        # Ensure the image did NOT get saved
        self.assertFalse(path.exists(path.join(TEMP_DIR, image_filename)))
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        # Ensure there are two resources since the image should remain external
        self.assertEqual(2, len(glb.resources))
        # Ensure embedded GLB resource was parsed correctly
        resource = glb.get_glb_resource()
        self.assertIsInstance(resource, GLBResource)
        # Ensure the image resource remains external
        image_resource = glb.get_resource(image_filename)
        self.assertIsInstance(image_resource, FileResource)
        # Ensure image is retained in the model structure
        image = glb.model.images[0]
        self.assertIsInstance(image, Image)
        self.assertEqual(image_filename, image.uri)
        # Ensure image filename is retained after export
        self.assertEqual(image_filename, image_resource.filename)
        # Loading the resource should raise FileNotFoundError since the image was not actually saved
        with self.assertRaises(FileNotFoundError):
            _ = image_resource.load()

    def test_export_glb_with_resource_not_yet_loaded(self):
        """
        Embedding resources should work when converting a glTF with external file resources that were not explicitly
        loaded when calling GLTF.load(). (This implies the resource will need to be implicitly loaded.)
        """
        # Arrange
        # Load a glTF model with load_file_resources set to False
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=False)
        # Ensure resource is initially not loaded
        resource = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)

        # Act
        # Convert the glTF to a GLB
        filename = path.join(TEMP_DIR, 'sample10.glb')
        exported_glb = gltf.export(filename)

        # Assert
        # Extract the image data from the exported GLB
        glb_resource = exported_glb.get_glb_resource()
        image = exported_glb.model.images[0]
        image_buffer_view = exported_glb.model.bufferViews[image.bufferView]
        offset = image_buffer_view.byteOffset
        bytelen = image_buffer_view.byteLength
        extracted_image_data = glb_resource.data[offset:(offset+bytelen)]
        # Ensure image data matches
        resource.load()
        self.assertEqual(resource.data, extracted_image_data)

    def test_export_glb_with_resource_not_yet_loaded_without_embedding(self):
        """
        When converting a glTF with external file resources that were not explicitly loaded when calling GLTF.load(),
        then converting the glTF to a GLB with the image resource remaining external, it should be loaded and copied
        when calling export_glb.
        """
        # Arrange
        # Load a glTF model with load_file_resources set to False
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=False)
        # Resource should initially not be loaded
        resource = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)

        # Act
        # Convert the glTF to a GLB without embedding the resource. However, set save_file_resources to True, so
        # the image should still get loaded and saved.
        filename = path.join(TEMP_DIR, 'sample11.glb')
        exported_glb = gltf.export_glb(filename, embed_image_resources=False, save_file_resources=True)

        # Assert
        # Original image resource should not be loaded
        self.assertFalse(resource.loaded)
        # Exported image resource should be loaded
        exported_resource = exported_glb.get_resource('CesiumLogoFlat.png')
        self.assertTrue(exported_resource.loaded)
        # Ensure image got saved
        image_filename = path.join(TEMP_DIR, 'CesiumLogoFlat.png')
        self.assertTrue(path.exists(image_filename))
        with open(sample('BoxTextured/CesiumLogoFlat.png'), 'rb') as f:
            original_texture_data = f.read()
        with open(image_filename, 'rb') as f:
            texture_data = f.read()
        self.assertEqual(original_texture_data, texture_data)

    def test_resource_remains_not_loaded_when_exporting_glb_without_embedding_or_saving_file_resources(self):
        """
        When converting a glTF with external file resources that were not explicitly loaded when calling GLTF.load(),
        the resources should remain not loaded if exporting without embedding or saving image resources.
        """
        # Arrange
        # Load a glTF model with load_file_resources set to False
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=False)
        # Resource should initially not be loaded
        resource = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)

        # Act
        # Convert the glTF to a GLB without embedding or saving image resources
        filename = path.join(TEMP_DIR, 'sample12.glb')
        gltf.export_glb(filename, embed_image_resources=False, save_file_resources=False)

        # Assert
        # Ensure resource remains not loaded
        self.assertFalse(resource.loaded)

    def test_export_gltf_raises_error_if_glb_resource_is_present(self):
        """
        When exporting a model as glTF, it may not have a GLB resource (the GLB resource needs to be converted to either
        a FileResource or EmbeddedResource first).
        """
        # Arrange
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(byteLength=4)])
        resource = GLBResource(b'data')
        gltf = GLTF(model=model, resources=[resource])

        # Act/Assert
        filename = path.join(TEMP_DIR, 'sample13.gltf')
        with self.assertRaises(TypeError):
            gltf.export(filename)

    def test_export_glb_with_multiple_glb_resources(self):
        """Test exporting a GLB with multiple GLB resources with different types."""
        # Arrange
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(byteLength=4)])
        glb_resource_1 = GLBResource(b'data')
        glb_resource_2 = GLBResource(b'more data', resource_type=123)
        gltf = GLTF(model=model, resources=[glb_resource_1, glb_resource_2])

        # Act
        filename = path.join(TEMP_DIR, 'sample14.glb')
        gltf2 = gltf.export(filename)

        # Assert
        # Exported model should have two GLB resources
        self.assertEqual(2, len(gltf2.resources))
        exported_glb_resource_1 = gltf2.resources[0]
        exported_glb_resource_2 = gltf2.resources[1]
        self.assertIsInstance(exported_glb_resource_1, GLBResource)
        self.assertIsInstance(exported_glb_resource_2, GLBResource)
        # Chunk types of both resources should be retained
        self.assertEqual(GLB_BINARY_CHUNK_TYPE, exported_glb_resource_1.resource_type)
        self.assertEqual(123, exported_glb_resource_2.resource_type)

    def test_load_glb_with_multiple_glb_resources(self):
        """Test loading a GLB with multiple GLB resources with different types."""
        # Act
        gltf = GLTF.load(sample('MultipleChunks/MultipleChunks.glb'))

        # Assert
        # Model should have two GLB resources
        self.assertEqual(2, len(gltf.resources))
        self.assertEqual(2, len(gltf.glb_resources))
        self.assertEqual(gltf.resources, gltf.glb_resources)
        # Extract the resources and ensure they are the correct type
        glb_resource_1 = gltf.resources[0]
        glb_resource_2 = gltf.resources[1]
        self.assertIsInstance(glb_resource_1, GLBResource)
        self.assertIsInstance(glb_resource_2, GLBResource)
        # Validate chunk types
        self.assertEqual(GLB_BINARY_CHUNK_TYPE, glb_resource_1.resource_type)
        self.assertEqual(123, glb_resource_2.resource_type)
        # Validate chunk data
        self.assertEqual(b'data', glb_resource_1.data)
        self.assertEqual(b'more data\x00\x00\x00', glb_resource_2.data)


# TODO:
#  - Add support for Base64Resource
#  - Test data URIs getting converted to embedded GLB resources
#  - Test auto-determining MIME type when embedding an image
#  - Test exporting model with multiple GLBResource - should throw if both GLBResource have the same resource type
