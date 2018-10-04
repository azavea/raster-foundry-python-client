raster-foundry-python-client
============================

A Python client for `Raster Foundry <https://www.rasterfoundry.com/>`_, a web platform for combining, analyzing, and publishing raster data.

Usage
-----

.. code-block:: python

   from rasterfoundry.api import API
   refresh_token = '<>'

   api = API(refresh_token=refresh_token)

   # List all projects
   my_projects = api.projects

   one_project = my_projects[0]

   # Get TMS URl without token
   one_project.tms()

Versions
~~~~~~~~

The latest version of `rasterfoundry` always points to the most recently released swagger spec in
the raster-foundry/raster-foundy-api-spec repository. If you need to point to a different spec
version, either install a version of the python client that refers to the appropriate spec, or
set the `RF_API_SPEC_PATH` environment variable to a url or local file path pointing to the
version of the spec that you want to use.

Generally this shouldn't matter, because the Raster Foundry API shouldn't have breaking changes.


Installation
------------

Without notebook support
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

   $ pip install rasterfoundry

With notebook support
~~~~~~~~~~~~~~~~~~~~~

Notebook support requires [`npm`](https://www.npmjs.com/get-npm).

.. code:: bash

   $ pip install rasterfoundry[notebook]

Then, enable widgets and leaflet in in jupyter notebooks:

.. code:: bash

   $ jupyter nbextension install --py --symlink --sys-prefix widgetsnbextension
   $ jupyter nbextension enable --py --sys-prefix widgetsnbextension 
   $ jupyter nbextension install --py --symlink --sys-prefix ipyleaflet
   $ jupyter nbextension enable --py --sys-prefix ipyleaflet


Testing
-------

The test suite execution process is managed by ``tox``:

.. code:: bash

   $ tox
