Usage Guide
===========

The first version supports search, metadata inspection, link discovery, EPUB
download, EPUB validation, mirror checks, and read-only category/format listing.
Search can target one or more titles, authors, author IDs, categories, formats,
or title and author together.

Search
------

Basic searches:

.. code-block:: bash

   vnthuquan search "cthulhu"
   vnthuquan search --title "Mưa Đỏ" --exact
   vnthuquan search --author "Kim Dung" --format epub
   vnthuquan search --category 23 --format epub --page 1 --limit 10

Repeated flags search for any matching value in that selector family:

.. code-block:: bash

   vnthuquan search --title "Mưa Đỏ" --title "Ăn Mày Dĩ Vãng"
   vnthuquan search --author "Kim Dung" --author "Chu Lai" --format epub --format pdf
   vnthuquan search --author-id 42 --author-id 1600 --limit 10
   vnthuquan search --category 23 --category 26 --format epub --limit 10

Formats can be repeated or comma-separated:

.. code-block:: bash

   vnthuquan search --author "Kim Dung" --format pdf,epub
   vnthuquan search --author "Kim Dung" --format pdf --format epub

Different selector families are combined where metadata is available:

.. code-block:: bash

   vnthuquan search \
      --author "Kim Dung" \
      --author "Chu Lai" \
      --format epub,pdf \
      --limit 10

Search both title and author fields:

.. code-block:: bash

   vnthuquan search "Chu Lai" --all --limit 10
   vnthuquan search "Mưa Đỏ" "Thiên Long Bát Bộ" --all --format epub

JSON output:

.. code-block:: bash

   vnthuquan --json search --title "Mưa Đỏ" --title "Thiên Long Bát Bộ" --format epub

Python wrapper examples:

.. code-block:: python

   from vnthuquan import VnThuQuanClient

   client = VnThuQuanClient()

   results = client.search(
      titles=["Mưa Đỏ", "Thiên Long Bát Bộ"],
      formats=["epub"],
      limit=10,
   )

   author_results = client.search_by_author(
      ["Kim Dung", "Chu Lai"],
      formats="epub,pdf",
      limit=10,
   )

Show metadata and links
-----------------------

.. code-block:: bash

   vnthuquan show --title "Lời hiệu triệu của Cthulhu" --links

Dry-run download
----------------

Downloads are dry-run by default. ``--dry-run`` is accepted when you want to
make that behavior explicit.

.. code-block:: bash

   vnthuquan download \
      --title "Lời hiệu triệu của Cthulhu" \
      --format epub \
      --out ~/Downloads \
      --dry-run

Execute download
----------------

.. code-block:: bash

   vnthuquan download \
      --title "Lời hiệu triệu của Cthulhu" \
      --format epub \
      --out ~/Downloads \
      --execute

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
   vnthuquan list category 23 --format epub --page 1
   vnthuquan list author 284 --format epub --page 1
   vnthuquan list format epub --page 1 --limit 10
   vnthuquan search --category 23 --format epub
   vnthuquan search --category 23 --category 26 --format epub --page 1
   vnthuquan search --author-id 42 --author-id 1600 --format epub --page 1
   vnthuquan search --format pdf,epub --page 1 --limit 10

Site lists
----------

.. code-block:: bash

   vnthuquan list latest --page 1 --limit 10
   vnthuquan list authors --initial A --page 1
   vnthuquan list title-initial A --format epub --page 1
   vnthuquan list most-viewed --page 1 --limit 10
   vnthuquan list five-star --page 1 --limit 10

Derived top lists scan global ranked pages and filter locally:

.. code-block:: bash

   vnthuquan list top --category 6 --source most-viewed --scan-pages 20 --limit 10
   vnthuquan list top --author-id 284 --source most-viewed --scan-pages 20 --limit 10
