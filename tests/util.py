from os import path


# Temporary directory used for tests
TEMP_DIR = 'tests/temp'

# Directory containing sample files used for tests
SAMPLES_DIR = 'tests/samples'


# Helper function for returning path to a sample file
def sample(filename):
    return path.join(SAMPLES_DIR, filename)
