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
* ``archive_path``
* ``timeout``
* ``retries``
* ``retry_backoff_seconds``
* ``retry_jitter_seconds``
* ``request_interval_seconds``
* ``cache_ttl_seconds``
* ``cache_path``
* ``filename_template``

``request_interval_seconds`` defaults to ``0.2`` to keep live-site requests
polite. ``cache_ttl_seconds`` defaults to ``0`` and can be increased to reuse
non-streaming search/list/metadata responses. When cache TTL is enabled without
an explicit ``cache_path``, the default persistent cache path is
``~/.cache/vnthuquan/http-cache.json``.

The default archive path is:

.. code-block:: text

   ~/.local/share/vnthuquan/downloads.jsonl

``filename_template`` supports ``{title}``, ``{author}``, ``{format}``, and
``{tid}``.

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
   vnthuquan config set archive_path ~/.local/share/vnthuquan/downloads.jsonl
   vnthuquan config set request_interval_seconds 0.5
   vnthuquan config set cache_ttl_seconds 300
   vnthuquan config set retry_backoff_seconds 0.5
   vnthuquan config set filename_template "{title} - {author} [{format}] [{tid}]"
   vnthuquan config unset download_dir
