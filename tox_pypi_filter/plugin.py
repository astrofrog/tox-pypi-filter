import os
import sys
import time
import socket
import tempfile
import subprocess

import pluggy
from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    pass

hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_addoption(parser):
    parser.add_argument('--pypi-filter', dest='pypi_filter',
                        help=('Like --force-dep, but will be applied regardless '
                              'of whether the dependency is declared or not in '
                              'the tox.ini file. This can be used to pin/constrain '
                              'package versions for packages defined in e.g. '
                              'extras_requires or even ones that are dependencies '
                              'of specified dependencies. If giving multiple constraints, '
                              'you can separate them with semicolons (;).'))


SERVER_PROCESS = None


@hookimpl
def tox_configure(config):

    global SERVER_PROCESS

    if config.option.pypi_filter is None:
        return

    # Write out requirements to file
    reqfile = tempfile.mktemp()
    with open(reqfile, 'w') as f:
        f.write(os.linesep.join(config.option.pypi_filter.split(';')))

    # Find available port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()

    # Run pypicky
    print('Starting tox-pypi-filter server')
    SERVER_PROCESS = subprocess.Popen(['pypicky', reqfile, '--port', str(port), '--quiet'])

    # FIXME: properly check that the server has started up
    time.sleep(2)

    config.indexserver['default'].url = f'http://localhost:{port}'


@hookimpl
def tox_cleanup(session):
    if SERVER_PROCESS is not None:
        print('Shutting down tox-pypi-filter server')
        SERVER_PROCESS.terminate()
