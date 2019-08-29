About tox-pypi-filter
=====================

About
-----

Tox includes a ``--force-dep`` option that can be used to provide version
restrictions for dependencies - however, by design this only works with
dependencies explicitly listed in the ``deps`` section of the ``tox.ini`` file
(see `this issue <https://github.com/tox-dev/tox/issues/534>`_ for a
discussion of this).

The **tox-pypi-filter** plugin works around this by using a proxy PyPI server
that filters packages in a way that is independent of tox's implementation.

Installing
----------

To install::

    pip install tox-pypi-filter

Using
-----

This plugin provides a ``--pypi-filter`` command-line option that takes
`PEP440 version specifiers
<https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_ separated by
semicolons, e.g.::

    tox --pypi-filter "numpy==1.14.*;pytest<4" -e py37-test

In this case, if Numpy or PyTest are needed by the tox environment, the versions
that will be installed will satisfy the version specification supplied.

Caveats
-------

This plugin will not work properly if you use the ``-i/--index-url`` option
manually when calling tox. In addition, this will only work with pip-based
installs, and will not work with e.g. `tox-conda
<https://github.com/tox-dev/tox-conda>`_.
