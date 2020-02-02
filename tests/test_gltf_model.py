import json
from unittest import TestCase
from .util import sample
from gltflib import GLTF, GLTFModel, Asset, Buffer


class TestGLTFModel(TestCase):
    def test_init(self):
        """
        Basic test ensuring the successful initialization of a GLTF2 model when all required properties are passed
        in. Note the only required property in a GLTF2 model is the asset.
        """
        # Act
        model = GLTFModel(asset=Asset())

        # Assert
        self.assertIsInstance(model, GLTFModel)

    def test_asset_version_default(self):
        """Ensures asset version is initialized as 2.0 if not passed in"""
        # Act
        model = GLTFModel(asset=Asset())

        # Assert
        self.assertEqual(model.asset.version, '2.0')

    def test_asset_version(self):
        """Ensures asset version is retained if a value is passed in"""
        # Act
        model = GLTFModel(asset=Asset(version='2.1'))

        # Assert
        self.assertEqual(model.asset.version, '2.1')

    def test_to_json_removes_empty_properties(self):
        """
        Ensures that any properties in the model that are "empty" (empty strings, lists, etc.) are deleted when
        encoding the model to JSON.
        """
        # Arrange
        model = GLTFModel(asset=Asset(generator='', minVersion=None), buffers=[])

        # Act
        v = model.to_json()

        # Assert
        data = json.loads(v)
        self.assertDictEqual(data, {'asset': {'version': '2.0'}})

    def test_decode(self):
        """Ensures that a simple model can be decoded successfully from JSON."""
        # Arrange
        v = '{"asset": {"version": "2.1"}, "buffers": [{ "uri": "triangle.bin", "byteLength": 44 }]}'

        # Act
        model = GLTFModel.from_json(v)

        # Assert
        self.assertEqual(model, GLTFModel(asset=Asset(version='2.1'), buffers=[Buffer(uri='triangle.bin', byteLength=44)]))

    def test_decode_missing_required_property(self):
        """
        Ensures that a warning is emitted when decoding a model from JSON if any required properties are missing.
        In this case, the "asset" property on the model is missing.
        """
        # Arrange
        v = '{}'

        # Act/Assert
        with self.assertWarnsRegex(RuntimeWarning, "non-optional type asset"):
            _ = GLTFModel.from_json(v)

    def test_load_skins(self):
        """Ensures skin data is loaded"""
        # Act
        gltf = GLTF.load(sample('RiggedSimple/glTF/RiggedSimple.gltf'))

        # Assert
        self.assertEqual(1, len(gltf.model.skins))
        skin = gltf.model.skins[0]
        self.assertEqual(13, skin.inverseBindMatrices)
        self.assertEqual(2, skin.skeleton)
        self.assertCountEqual([2, 3], skin.joints)
