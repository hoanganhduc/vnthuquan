CLI Reference
=============

Global options
--------------

.. code-block:: text

   --json
   --verbose
   --quiet
   --debug
   --no-color
   --config PATH
   --timeout SECONDS
   --retries N

Commands
--------

``search``
~~~~~~~~~~

.. code-block:: bash

   vnthuquan search "cthulhu" --field title --format epub --limit 10

``show``
~~~~~~~~

.. code-block:: bash

   vnthuquan show --title "..." --links
   vnthuquan show --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --assets

``download``
~~~~~~~~~~~~

.. code-block:: bash

   vnthuquan download --title "..." --format epub --out ~/Downloads
   vnthuquan download --title "..." --format epub --out ~/Downloads --execute

``validate``
~~~~~~~~~~~~

.. code-block:: bash

   vnthuquan validate ~/Downloads/book.epub

``categories`` and ``formats``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   vnthuquan categories list
   vnthuquan categories show 23
   vnthuquan formats list

``mirrors``
~~~~~~~~~~~

.. code-block:: bash

   vnthuquan mirrors list
   vnthuquan mirrors check
   vnthuquan mirrors use http://vnthuquan.net
   vnthuquan mirrors reset

Exit codes
----------

.. code-block:: text

   0 success
   1 general error
   2 CLI usage error
   3 not found
   4 ambiguous result
   5 network/mirror error
   6 download error
   7 validation error
   8 filesystem error
   9 config error
