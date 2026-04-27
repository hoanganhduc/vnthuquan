Mirrors
=======

Known mirrors:

.. code-block:: text

   http://vietnamthuquan.eu
   http://vnthuquan.net

Commands:

.. code-block:: bash

   vnthuquan mirrors list
   vnthuquan mirrors check
   vnthuquan mirrors use http://vnthuquan.net
   vnthuquan mirrors reset

Downloads automatically retry other known mirrors after download or validation
failures. The client re-discovers metadata and assets on the new mirror instead
of guessing a replacement host. Use ``vnthuquan download --no-failover`` to
disable this behavior. A command-level ``--mirror`` is treated as pinned and is
not silently changed.
