import os
import shutil
from os import path


# Temporary directory used for tests (cleared on every run)
TEMP_DIR = 'tests/temp'

# Directory containing the official glTF sample files. These samples are the same ones that are available here:
# https://github.com/KhronosGroup/glTF-Sample-Models
SAMPLES_DIR = 'tests/samples/glTF-Sample-Models/2.0'

# Custom sample models used for tests
CUSTOM_SAMPLES_DIR = 'tests/samples/custom'


def sample(model, fmt='glTF'):
    """
    Helper function for returning the path to an official sample model from the glTF-Sample-Models directory in the
    specified format (defaults to glTF).
    :param model: Model name
    :param fmt: Format (either 'glTF', 'glTF-Binary', 'glTF-Embedded', or 'glTF-Draco'. Defaults to 'glTF')
    :return: Model filename
    """
    ext = '.glb' if fmt == 'glTF-Binary' else '.gltf'
    return path.join(SAMPLES_DIR, model, fmt, model + ext)


def custom_sample(filename):
    """
    Helper function for returning the path to a custom sample model (as opposed to an official sample model from the
    glTF-Sample-Models repository, as returned by sample). This simply adds the CUSTOM_SAMPLES_DIR base directory to
    the specified path.
    :param filename: Filename of the sample model. This should also include the subdirectory (e.g.,
        "Minimal/minimal.gltf")
    :return: Full filename for the custom model
    """
    return path.join(CUSTOM_SAMPLES_DIR, filename)


def setup_temp_dir():
    """Creates TEMP_DIR (if it does not already exist) and ensures it is empty."""
    if path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)
