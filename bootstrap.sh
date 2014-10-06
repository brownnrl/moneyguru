#!/bin/bash

command -v python3 -m venv >/dev/null 2>&1 || { echo >&2 "Python 3.3 required. Install it and try again. Aborting"; exit 1; }

if [ -d "deps" ]; then
    # We have a collection of dependencies in our source package. We might as well use it instead
    # of downloading it from PyPI.
    PIPARGS="--no-index --find-links=deps"
fi

if [ ! -d "env" ]; then
    echo "No virtualenv. Creating one"
    python3 -m venv --system-site-packages env
    source env/bin/activate
    # With a new venv, we want to force (without checking if it exists first) installing a venv pip
    # or else we'll end up with the system one.
    python get-pip.py $PIPARGS --force-reinstall
else
    echo "Activating env"
    source env/bin/activate
fi

command -v pip
if [ $? -ne 0 ]; then
    echo "pip not installed. Installing."
    python get-pip.py $PIPARGS
fi

echo "Installing pip requirements"
if [ "$(uname)" == "Darwin" ]; then
    pip install -r requirements-osx.txt
else
    python3 -c "import PyQt4" >/dev/null 2>&1 || { echo >&2 "PyQt 4.8+ required. Install it and try again. Aborting"; exit 1; }
    pip install $PIPARGS -r requirements.txt
fi

echo "Bootstrapping complete! You can now configure, build and run moneyGuru with:"
echo ". env/bin/activate && python configure.py && python build.py && python run.py"
