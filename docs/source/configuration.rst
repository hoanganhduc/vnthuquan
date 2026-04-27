Configuration
=============

Config file
-----------

The default config path is:

.. code-block:: text

   ~/.config/vnthuquan/config.json

Supported keys:

* ``default_mirror``
* ``download_dir``
* ``timeout``
* ``retries``
* ``request_interval_seconds``
* ``cache_ttl_seconds``

``request_interval_seconds`` defaults to ``0.2`` to keep live-site requests
polite. ``cache_ttl_seconds`` defaults to ``0`` and can be increased to reuse
non-streaming search/list/metadata responses within a short session.

Download directory resolution
-----------------------------

The output directory is resolved in this order:

1. ``--out``
2. config ``download_dir``
3. ``VNTHUQUAN_DOWNLOAD_DIR``
4. ``~/Downloads/vnthuquan``

Commands
--------

.. code-block:: bash

   vnthuquan config path
   vnthuquan config show
   vnthuquan config set download_dir ~/Downloads/vnthuquan
   vnthuquan config set request_interval_seconds 0.5
   vnthuquan config set cache_ttl_seconds 300
   vnthuquan config unset download_dir
