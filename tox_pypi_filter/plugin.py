import os
import sys
import time
import socket
import tempfile
import subprocess
import urllib.parse
import urllib.request
from textwrap import indent

from tox.plugin import impl
from tox.config.cli.parser import ToxParser
from tox.config.sets import ConfigSet, EnvConfigSet
from tox.session.state import State

from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    pass


HELP = ("Specify version constraints for packages which are then applied by "
        "setting up a proxy PyPI server. If giving multiple constraints, you "
        "can separate them with semicolons (;). This can also be a URL to a "
        "local file (e.g. file:// or file:///) or a remote file (e.g. "
        "http://, https://, or ftp://).")


@impl
def tox_add_option(parser: ToxParser) -> None:
    parser.add_argument('--pypi-filter', action="store", type=str, of_type=str)


@impl
def tox_add_core_config(core_conf: ConfigSet, state: State) -> None:
    core_conf.add_config('pypi_filter', 'string', default="", desc=HELP)


SERVER_PROCESS = {}


@impl
def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:
    # Skip the environment used for creating the tarball
    if env_conf.name == ".pkg":
        return

    global SERVER_PROCESS

    pypi_filter_config = state.conf.core["pypi_filter"]
    pypi_filter_cli = state.conf.options.pypi_filter

    pypi_filter = pypi_filter_cli or pypi_filter_config

    if not pypi_filter:
        return

    url_info = urllib.parse.urlparse(pypi_filter)

    if url_info.scheme == 'file':
        reqfile = url_info.netloc + url_info.path
    elif url_info.scheme:
        reqfile = urllib.request.urlretrieve(url_info.geturl())[0]
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
    print(f"{env_conf.name}: Starting tox-pypi-filter server with the following requirements:")
    print(indent(contents.strip(), '  '))

    SERVER_PROCESS[env_conf.name] = subprocess.Popen([sys.executable, '-m', 'pypicky',
                                                      reqfile, '--port', str(port), '--quiet'])

    # FIXME: properly check that the server has started up
    time.sleep(2)

    env_config = env_conf.load("setenv")
    if "PIP_INDEX_URL" in env_config:
        raise ValueError("Can not use tox-pypi-filter if already setting the PIP_INDEX_URL env var.")
    env_config.update({"PIP_INDEX_URL": f'http://localhost:{port}'})


@impl
def tox_after_run_commands(tox_env, exit_code, outcomes):
    print("After run commands")
    global SERVER_PROCESS

    proc = SERVER_PROCESS.pop(tox_env.name, None)
    if proc:
        print(f"{tox_env.name}: Shutting down tox-pypi-filter server")
        proc.terminate()
