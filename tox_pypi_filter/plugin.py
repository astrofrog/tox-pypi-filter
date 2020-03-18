import os
import time
import socket
import tempfile
import subprocess
import urllib.parse
import urllib.request

import pluggy
from pkg_resources import DistributionNotFound, get_distribution

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
    parser.add_argument('--pypi-filter-requirements', dest='pypi_filter_req',
                        help=('Like --force-dep, but will be applied regardless '
                              'of whether the dependency is declared or not in '
                              'the tox.ini file. This can be used to pin/constrain '
                              'package versions for packages defined in e.g. '
                              'extras_requires or even ones that are dependencies '
                              'of specified dependencies. Can be a local '
                              'requirements file or a URL to one.'))


SERVER_PROCESS = None


@hookimpl
def tox_configure(config):

    global SERVER_PROCESS

    if config.option.pypi_filter is None and config.option.pypi_filter_req is None:
        return

    if config.option.pypi_filter and config.option.pypi_filter_req:
        raise ValueError("Please specify only one of --pypi-filter or --pypi-filter-requirements")

    if config.option.pypi_filter:
        # Write out requirements to file
        reqfile = tempfile.mktemp()
        with open(reqfile, 'w') as f:
            f.write(os.linesep.join(config.option.pypi_filter.split(';')))

    if config.option.pypi_filter_req:
        url_info = urllib.parse.urlparse(config.option.pypi_filter_req)
        if url_info.scheme:
            reqfile, _ = urllib.request.urlretrieve(url_info.geturl())
        else:
            reqfile = url_info.path

    # If we get a blank set of requirements then we don't do anything.
    with open(reqfile, "r") as fobj:
        contents = fobj.read()
        if not contents:
            return

    print(f"tox-pypi-filter is enforcing the following version requirements:\n{contents}".strip())

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
