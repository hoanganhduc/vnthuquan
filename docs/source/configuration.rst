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
   vnthuquan config unset download_dir
