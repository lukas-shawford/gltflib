import os
import shutil
import json
from os import path
from unittest import TestCase
from gltflib import GLTF, GLTFModel, Asset, FileResource, ExternalResource, Buffer, BufferView, Image, GLBResource


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
        gltf = GLTF.load(sample('Minimal/minimal.gltf'))
        self.assertIsInstance(gltf, GLTF)
        self.assertEqual(GLTFModel(asset=Asset(version="2.0")), gltf.model)

    def test_export(self):
        """Basic test ensuring the class can successfully save a minimal GLTF 2.0 file."""
        gltf = GLTF(model=GLTFModel(asset=Asset(version="2.0")))
        filename = path.join(TEMP_DIR, 'minimal.gltf')
        gltf.export(filename)
        self.assert_gltf_files_equal(sample('Minimal/minimal.gltf'), filename)

    def test_load_file_resource(self):
        """External files referenced in a glTF model should be loaded as FileResource"""
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'))
        self.assertIsInstance(gltf.resources, list)
        resource = gltf.get_resource('triangleWithoutIndices.bin')
        self.assertIsInstance(resource, FileResource)
        self.assertEqual('triangleWithoutIndices.bin', resource.filename)

    def test_load_file_resource_no_autoload(self):
        """File resource contents should not be autoloaded by default"""
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'))
        resource = gltf.get_resource('triangleWithoutIndices.bin')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)
        self.assertIsNone(resource.data)

    def test_load_file_resource_with_autoload(self):
        """When load_file_resources is true, file resource contents should be autoloaded"""
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'), load_file_resources=True)
        resource = gltf.get_resource('triangleWithoutIndices.bin')
        self.assertIsInstance(resource, FileResource)
        self.assertTrue(resource.loaded)
        with open(sample('TriangleWithoutIndices/triangleWithoutIndices.bin'), 'rb') as f:
            data = f.read()
        self.assertEqual(data, resource.data)

    def test_load_image_resources(self):
        """Ensure image resources are loaded"""
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=True)
        texture = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(texture, FileResource)
        with open(sample('BoxTextured/CesiumLogoFlat.png'), 'rb') as f:
            texture_data = f.read()
        self.assertEqual(texture_data, texture.data)

    def test_load_embedded_resources(self):
        """Embedded resources should not be parsed (for now?)"""
        gltf = GLTF.load(sample('BoxTexturedEmbedded/BoxTextured.gltf'))
        self.assertEqual(0, len(gltf.resources))

    def test_load_external_resources(self):
        """External resources should be parsed as ExternalResource instances, but otherwise ignored (for now)"""
        gltf = GLTF.load(sample('BoxTexturedExternal/BoxTextured.gltf'))
        uri = 'https://www.example.com'
        resource = gltf.get_resource(uri)
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
        data = b'sample binary data'
        resource = FileResource('triangleWithoutIndices.bin', data=data)
        gltf = GLTF.load(sample('TriangleWithoutIndices/TriangleWithoutIndices.gltf'), resources=[resource])
        loaded_resource = gltf.get_resource('triangleWithoutIndices.bin')
        self.assertIs(loaded_resource, resource)
        self.assertEqual(data, loaded_resource.data)
        self.assertIsInstance(loaded_resource, FileResource)
        self.assertTrue(loaded_resource.loaded)

    def test_export_file_resources(self):
        """Test exporting a GLTF model with external file resources"""
        data = b'sample binary data'
        bytelen = len(data)
        resource = FileResource('buffer.bin', data=data)
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)])
        gltf = GLTF(model=model, resources=[resource])
        filename = path.join(TEMP_DIR, 'sample.gltf')
        gltf.export(filename, save_file_resources=True)
        resource_filename = path.join(TEMP_DIR, 'buffer.bin')
        self.assertTrue(path.exists(resource_filename))
        with open(resource_filename, 'rb') as f:
            self.assertEqual(data, f.read())

    def test_export_file_resources_skip(self):
        """
        Ensure external file resources are skipped when exporting a GLTF model with save_file_resources set to False
        """
        resource_filename = path.join(TEMP_DIR, 'buffer.bin')
        if path.exists(resource_filename):
            os.remove(resource_filename)
        data = b'sample binary data'
        bytelen = len(data)
        resource = FileResource('buffer.bin', data=data)
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)])
        gltf = GLTF(model=model, resources=[resource])
        filename = path.join(TEMP_DIR, 'sample.gltf')
        gltf.export(filename, save_file_resources=False)
        self.assertFalse(path.exists(resource_filename))

    def test_validate_file_resources_in_buffer_when_exporting(self):
        """
        Test validation for missing external resources referenced in the buffers array when exporting with
        save_file_resources set to True
        """
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=1024)])
        gltf = GLTF(model=model)
        filename = path.join(TEMP_DIR, 'sample.gltf')
        with self.assertRaisesRegex(RuntimeError, 'Missing resource'):
            gltf.export(filename, save_file_resources=True)

    def test_validate_file_resources_in_image_when_exporting(self):
        """
        Test validation for missing external resources referenced in the images array when exporting with
        save_file_resources set to True
        """
        model = GLTFModel(asset=Asset(version='2.0'), images=[Image(uri='buffer.bin')])
        gltf = GLTF(model=model)
        filename = path.join(TEMP_DIR, 'sample.gltf')
        with self.assertRaisesRegex(RuntimeError, 'Missing resource'):
            gltf.export(filename, save_file_resources=True)

    def test_load_glb(self):
        """Ensure a model can be loaded from a binary glTF (GLB) file"""
        gltf = GLTF.load(sample('Box/glb/Box.glb'))
        self.assertEqual('2.0', gltf.model.asset.version)
        self.assertIsNone(gltf.model.buffers[0].uri)
        self.assertEqual(648, gltf.model.buffers[0].byteLength)
        resources = gltf.get_glb_resources()
        self.assertEqual(1, len(resources))
        resource = resources[0]
        self.assertIsInstance(resource, GLBResource)
        self.assertEqual(648, len(resource.data))

    def test_export_glb(self):
        """Basic test to ensure a model can be saved in GLB format"""
        data = b'sample binary data'
        bytelen = len(data)
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(uri='buffer.bin', byteLength=bytelen)])
        gltf = GLTF(model=model, resources=[FileResource(filename='buffer.bin', data=data)])
        filename = path.join(TEMP_DIR, 'sample.glb')
        gltf.export(filename)
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
        self.assertEqual(b'sample binary data\x00\x00', resource.data)

    def test_export_glb_multiple_buffers(self):
        """
        Ensures that a model with multiple buffers and buffer views is exported correctly as GLB. The buffers should be
        merged into a single buffer, and all buffer views that reference the buffer should have their byte offsets
        adjusted.
        """
        data1 = b'sample binary data'
        bytelen1 = len(data1)
        data2 = b'some more binary data'
        bytelen2 = len(data2)
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
            FileResource(filename='buffer1.bin', data=data1),
            FileResource(filename='buffer2.bin', data=data2)
        ])
        filename = path.join(TEMP_DIR, 'sample2.glb')
        gltf.export(filename)
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        # The two buffers should be merged into one
        self.assertEqual(1, len(glb.model.buffers))
        # Buffer URI should be undefined since the data is now embedded
        buffer = glb.model.buffers[0]
        self.assertIsNone(buffer.uri)
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
        data = b'sample image data'
        bytelen = len(data)
        image_filename = 'image.png'
        model = GLTFModel(asset=Asset(version='2.0'), images=[Image(uri=image_filename)])
        gltf = GLTF(model=model, resources=[FileResource(filename=image_filename, data=data, mimetype='image/jpeg')])
        filename = path.join(TEMP_DIR, 'sample3.glb')
        gltf.export(filename)
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
        # Ensure image was transformed so it points to a buffer view instead of uri
        image = glb.model.images[0]
        self.assertIsInstance(image, Image)
        self.assertIsNone(image.uri)
        self.assertEqual(0, image.bufferView)
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
        # Export the GLB
        filename = path.join(TEMP_DIR, 'sample4.glb')
        gltf.export(filename)
        # Read the file back in and verify expected structure
        glb = GLTF.load_glb(filename)
        self.assertEqual(model.asset, glb.model.asset)
        self.assertEqual(1, len(glb.model.buffers))
        buffer = glb.model.buffers[0]
        self.assertIsInstance(buffer, Buffer)
        # Buffer URI should be undefined since the data is now embedded
        self.assertIsNone(buffer.uri)
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
        # Ensure image was transformed so it points to a buffer view instead of uri
        image = glb.model.images[0]
        self.assertIsInstance(image, Image)
        self.assertIsNone(image.uri)
        self.assertEqual(4, image.bufferView)

    def test_export_glb_with_existing_glb_buffer_and_resource(self):
        """
        Ensure that when exporting a GLB model with an existing GLBResource and a GLB buffer works correctly (existing
        buffer and resource should be preserved, and no new ones added)
        """
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(byteLength=4)])
        resource = GLBResource(b'data')
        gltf = GLTF(model=model, resources=[resource])
        filename = path.join(TEMP_DIR, 'sample5.glb')
        gltf.export(filename)
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
        # Sample buffer 1 data
        buffer_1_filename = 'buffer_1.bin'
        buffer_1_data = b'sample buffer one data'
        buffer_1_bytelen = len(buffer_1_data)
        # Sample buffer 2 data
        buffer_2_filename = 'buffer_2.bin'
        buffer_2_data = b'sample buffer two data'
        buffer_2_bytelen = len(buffer_2_data)
        # Sample image data (this will remain external)
        image_filename = 'sample6.png'
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
        # Export the GLB (do not embed image resources)
        filename = path.join(TEMP_DIR, 'sample6.glb')
        gltf.export_glb(filename, embed_image_resources=False)
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
        # Sample buffer 1 data (this will remain external)
        buffer_1_filename = 'sample_7_buffer_1.bin'
        buffer_1_data = b'sample buffer one data'
        buffer_1_bytelen = len(buffer_1_data)
        # Sample buffer 2 data (this will remain external)
        buffer_2_filename = 'sample_7_buffer_2.bin'
        buffer_2_data = b'sample buffer two data'
        buffer_2_bytelen = len(buffer_2_data)
        # Sample image data (this will remain external)
        image_filename = 'sample_7_image.png'
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
        # Export the GLB (do not embed buffer or image resources)
        filename = path.join(TEMP_DIR, 'sample7.glb')
        gltf.export_glb(filename, embed_buffer_resources=False, embed_image_resources=False)
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
        # Sample buffer data
        buffer_filename = 'buffer.bin'
        buffer_data = b'sample buffer one data'
        buffer_bytelen = len(buffer_data)
        # Sample image data (this will remain external, and we will skip actually saving it)
        image_filename = 'sample8.png'
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
        # Export the GLB (do not embed image resources, and skip saving file resources)
        filename = path.join(TEMP_DIR, 'sample8.glb')
        gltf.export_glb(filename, embed_image_resources=False, save_file_resources=False)
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
        When converting a glTF with external file resources that were not explicitly loaded when calling GLTF.load(),
        the resources should get automatically loaded when exporting to GLB.
        """
        # Load a glTF model with load_file_resources set to False
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=False)
        # Resource should initially not be loaded
        resource = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)
        # Convert the glTF to a GLB
        filename = path.join(TEMP_DIR, 'sample9.glb')
        gltf.export(filename)
        # Ensure resource got loaded
        self.assertTrue(resource.loaded)

    def test_export_glb_with_resource_not_yet_loaded_without_embedding(self):
        """
        When converting a glTF with external file resources that were not explicitly loaded when calling GLTF.load(),
        then converting the glTF to a GLB with the image resource remaining external, it should be loaded and copied
        when calling export_glb.
        """
        # Load a glTF model with load_file_resources set to False
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=False)
        # Resource should initially not be loaded
        resource = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)
        # Convert the glTF to a GLB without embedding the resource. However, set save_file_resources to True, so
        # the image should still get loaded and saved.
        filename = path.join(TEMP_DIR, 'sample10.glb')
        gltf.export_glb(filename, embed_image_resources=False, save_file_resources=True)
        # Ensure resource is now loaded
        self.assertTrue(resource.loaded)
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
        # Load a glTF model with load_file_resources set to False
        gltf = GLTF.load(sample('BoxTextured/BoxTextured.gltf'), load_file_resources=False)
        # Resource should initially not be loaded
        resource = gltf.get_resource('CesiumLogoFlat.png')
        self.assertIsInstance(resource, FileResource)
        self.assertFalse(resource.loaded)
        # Convert the glTF to a GLB without embedding or saving image resources
        filename = path.join(TEMP_DIR, 'sample11.glb')
        gltf.export_glb(filename, embed_image_resources=False, save_file_resources=False)
        # Ensure resource remains not loaded
        self.assertFalse(resource.loaded)

    def test_export_gltf_raises_error_if_glb_resource_is_present(self):
        """
        When exporting a model as glTF, it may not have a GLB resource (the GLB resource needs to be converted to either
        a FileResource or EmbeddedResource first).
        """
        model = GLTFModel(asset=Asset(version='2.0'), buffers=[Buffer(byteLength=4)])
        resource = GLBResource(b'data')
        gltf = GLTF(model=model, resources=[resource])
        filename = path.join(TEMP_DIR, 'sample12.gltf')
        with self.assertRaises(TypeError):
            gltf.export(filename)


# TODO:
#  - Test embedding file resources that are not yet loaded
#  - Test data URIs getting converted to embedded GLB resources
#  - Images can refer to a buffer view. Ensure these are merged properly when converting to GLB.
#  - Test handling multiple binary chunks in a GLB with different chunk types when loading and exporting
#  - Test saving a GLB that already has a GLB resource present (need to re-merge)
#  - Test auto-determining MIME type when embedding an image
#  - Ensure this requirement from the spec is met when embedding data:
#    The offset of an accessor into a bufferView (i.e., accessor.byteOffset) and the offset of an accessor into a buffer
#    (i.e., accessor.byteOffset + bufferView.byteOffset) must be a multiple of the size of the accessor's component
#    type.
