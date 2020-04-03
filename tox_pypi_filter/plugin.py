import os
import sys
import time
import socket
import tempfile
import subprocess
import urllib.parse
import urllib.request
from textwrap import indent

import pluggy
from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    pass

hookimpl = pluggy.HookimplMarker("tox")

HELP = ("Specify version constraints for packages which are then applied by "
        "setting up a proxy PyPI server. If giving multiple constraints, you "
        "can separate them with semicolons (;). This can also be a URL to a "
        "local file (e.g. file:// or file:///) or a remote file (e.g. "
        "http://, https://, or ftp://).")


@hookimpl
def tox_addoption(parser):
    parser.add_argument('--pypi-filter', dest='pypi_filter', help=HELP)
    parser.add_testenv_attribute('pypi_filter', 'string', help=HELP)


SERVER_PROCESS = []


@hookimpl
def tox_testenv_create(venv, action):
    global SERVER_PROCESS

    pypi_filter = venv.envconfig.config.option.pypi_filter or venv.envconfig.pypi_filter

    if not pypi_filter:
        return

    url_info = urllib.parse.urlparse(pypi_filter)

    if url_info.scheme:
        reqfile = urllib.request.urlretrieve(url_info.geturl())[0]
    elif pypi_filter.startswith('file://'):
        reqfile = url_info.path
    else:
        # Write out requirements to file
        reqfile = tempfile.mktemp()
        with open(reqfile, 'w') as f:
            f.write(os.linesep.join(pypi_filter.split(';')))

    # If we get a blank set of requirements then we don't do anything.
    with open(reqfile, "r") as fobj:
        contents = fobj.read()
        if not contents:
            return

    # Find available port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()

    # Run pypicky
    print('Starting tox-pypi-filter server with the following requirements:')
    print(indent(contents.strip(), '  '))

    SERVER_PROCESS.append(subprocess.Popen([sys.executable, '-m', 'pypicky',
                                            reqfile, '--port', str(port), '--quiet']))

    # FIXME: properly check that the server has started up
    time.sleep(2)

    venv.envconfig.config.indexserver['default'].url = f'http://localhost:{port}'


@hookimpl
def tox_cleanup(session):
    global SERVER_PROCESS
    for process in SERVER_PROCESS:
        print('Shutting down tox-pypi-filter server')
        process.terminate()
        SERVER_PROCESS = []
