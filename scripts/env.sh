#!/usr/bin/env bash

###############################################################################
# env.sh
# ------
#
# Activates the virtual Python environment (creating it if necessary) for the
# current terminal session and installs required dependencies. This file should
# be run using 'source' prior to executing the application. Assumes working
# directory is root of the project.
#
# USAGE: source scripts/env.sh
###############################################################################


# Create virtualenv if it has not already been created
if [[ ! -d env ]]; then
    python3 -m venv env
fi

# Activate virtualenv
source env/bin/activate

# Ensure wheel and setuptools are installed
pip install wheel==0.37.0 setuptools==57.4.0

# Install dependencies
pip install -r requirements.txt
