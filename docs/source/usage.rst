Usage Guide
===========

The first version supports search, metadata inspection, link discovery, EPUB
download, EPUB validation, mirror checks, and read-only category/format listing.

Search
------

.. code-block:: bash

   vnthuquan search "cthulhu"

Show metadata and links
-----------------------

.. code-block:: bash

   vnthuquan show --title "Lời hiệu triệu của Cthulhu" --links

Dry-run download
----------------

Downloads are dry-run by default.

.. code-block:: bash

   vnthuquan download --title "Lời hiệu triệu của Cthulhu" --format epub --out ~/Downloads

Execute download
----------------

.. code-block:: bash

   vnthuquan download --title "Lời hiệu triệu của Cthulhu" --format epub --out ~/Downloads --execute

Validate
--------

.. code-block:: bash

   vnthuquan validate ~/Downloads/book.epub

Categories and formats
----------------------

.. code-block:: bash

   vnthuquan categories list
   vnthuquan categories show 23
   vnthuquan formats list
