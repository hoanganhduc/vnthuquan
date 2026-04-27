Usage Guide
===========

The first version supports search, metadata inspection, link discovery, EPUB,
PDF, generated text, and audio downloads, mirror checks, and read-only
category/format listing.
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
   vnthuquan search --author "Kim Dung" --format epub --print title,url

Parallel search is explicit and should be used only for independent live-site
requests:

.. code-block:: bash

   vnthuquan search --category 23 --category 26 --format epub --jobs auto --limit 20

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

Filename templates
------------------

Use ``--filename-template`` to control output names. Supported fields are
``{title}``, ``{author}``, ``{format}``, and ``{tid}``.

.. code-block:: bash

   vnthuquan download \
      --title "Lời hiệu triệu của Cthulhu" \
      --format epub \
      --out ~/Downloads \
      --filename-template "{title} - {author} [{tid}]" \
      --dry-run

Queue manifests
---------------

Bulk downloads are intentionally split into a review step and an execute step.
``download --all`` writes a queue manifest only.

.. code-block:: bash

   vnthuquan download \
      --all \
      --category 23 \
      --format epub \
      --limit 20 \
      --manifest queue.json \
      --dry-run

.. code-block:: bash

   vnthuquan download \
      --from-manifest queue.json \
      --execute \
      --jobs auto \
      --progress

Downloads retry other known mirrors after download or validation failures. Use
``--no-failover`` to keep a failing download on the selected mirror. A
user-provided ``--mirror`` is treated as pinned and is not silently changed.

Other formats
-------------

Search the format first, then pass either the title, URL, or TID to
``download``. Dry-run first so the CLI can show the live asset URL, output path,
expected size when available, and planned validation.

.. code-block:: bash

   vnthuquan search --format pdf --limit 5
   vnthuquan search --format text --limit 5
   vnthuquan search --format audio --limit 5

.. code-block:: bash

   vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format pdf --out ~/Downloads --dry-run
   vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format text --out ~/Downloads --dry-run
   vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format audio --out ~/Downloads --dry-run

Use ``--execute`` after reviewing the dry-run plan:

.. code-block:: bash

   vnthuquan download --title "Some PDF Title" --format pdf --out ~/Downloads --execute
   vnthuquan download --title "Some Text Title" --format text --out ~/Downloads --execute
   vnthuquan download --title "Some Audio Title" --format audio --out ~/Downloads --execute

Format behavior:

* ``epub`` saves the direct EPUB asset.
* ``pdf`` saves the PDF source exposed by the site reader and reports when the reader disables direct download.
* ``text`` walks the site chapter list and writes one UTF-8 ``.txt`` export.
* ``audio`` packages discovered MP3 files into one ``.zip`` with a ``manifest.json``.
* ``image`` entries can be searched and listed, but executable image downloads are not implemented because the site does not expose one stable ebook-level image asset route.

For audio, dry-run first and check ``Expected size``; some bundles are hundreds
of MB. For text, validation proves the generated file is readable UTF-8, not
that the source site contains every canonical chapter.

Validate
--------

.. code-block:: bash

   vnthuquan validate ~/Downloads/book.epub
   vnthuquan validate ~/Downloads/book.pdf --format pdf
   vnthuquan validate ~/Downloads/book.txt --format text
   vnthuquan validate ~/Downloads/book.zip --format audio
   vnthuquan validate ~/Downloads/book.zip --format audio --strict
   vnthuquan validate ~/Downloads/book.epub --format epub --external

Archive
-------

Executed downloads are recorded in a JSONL archive unless ``--no-archive`` is
used.

.. code-block:: bash

   vnthuquan archive path
   vnthuquan archive list --limit 10
   vnthuquan archive list --limit 10 --print title,format,output_path,sha256

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
