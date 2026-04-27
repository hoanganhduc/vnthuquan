Listing
=======

``vnthuquan list`` exposes read-only listing routes from the live site.

Native lists
------------

.. code-block:: bash

   vnthuquan list latest --page 1 --limit 10
   vnthuquan list authors --initial A --page 1
   vnthuquan list title-initial A --format epub --page 1
   vnthuquan list category 23 --format epub --page 1
   vnthuquan list author 284 --format epub --page 1
   vnthuquan list format epub --page 1 --limit 10
   vnthuquan list most-viewed --page 1 --limit 10
   vnthuquan list five-star --page 1 --limit 10

Use ``#`` as the initial for numeric title or author indexes:

.. code-block:: bash

   vnthuquan list authors --initial '#'
   vnthuquan list title-initial '#'

Derived top lists
-----------------

The site exposes global most-viewed and five-star lists, but it does not expose
native per-category or per-author ranking routes. Derived top lists scan a
bounded number of global ranked pages and filter locally.

.. code-block:: bash

   vnthuquan list top --category 6 --source most-viewed --scan-pages 20 --limit 10
   vnthuquan list top --author-id 284 --source most-viewed --scan-pages 20 --limit 10
   vnthuquan list top --author "kim dung" --source five-star --scan-pages 20 --limit 10

Increase ``--scan-pages`` when a category or author has few entries in the first
ranked pages. The result is complete only for the pages scanned.

Python API
----------

.. code-block:: python

   from vnthuquan import VnThuQuanClient

   client = VnThuQuanClient()
   latest = client.list_latest(limit=10)
   authors = client.list_authors("A", limit=30)
   epub_titles = client.list_by_title_initial("A", formats="epub", limit=10)
   top_kiem_hiep = client.list_top_by_category(
      6,
      source="most-viewed",
      scan_pages=20,
      limit=10,
   )
