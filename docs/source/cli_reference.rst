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

Search accepts positional queries and named selectors. Repeating a selector
adds more accepted values for that selector, while ``--format`` can be repeated
or supplied as a comma-separated list.

.. code-block:: bash

   vnthuquan search "cthulhu" --field title --format epub --limit 10
   vnthuquan search --title "Mưa Đỏ" --exact
   vnthuquan search --title "Mưa Đỏ" --title "Ăn Mày Dĩ Vãng"
   vnthuquan search --author "Kim Dung" --format pdf,epub
   vnthuquan search --author "Kim Dung" --author "Chu Lai" --format epub --format pdf
   vnthuquan search --author-id 42 --author-id 1600 --limit 10
   vnthuquan search --category 23 --category 26 --format epub --page 1 --limit 10
   vnthuquan search "Chu Lai" --all --limit 10
   vnthuquan search "Mưa Đỏ" "Thiên Long Bát Bộ" --all --format epub
   vnthuquan search --format epub --page 1 --limit 10
   vnthuquan --json search --title "Mưa Đỏ" --title "Thiên Long Bát Bộ" --format epub

Search option summary:

.. code-block:: text

   query                 Search query; repeat for multiple title/all-field queries
   --title TEXT          Search by title; repeat for multiple titles
   --author TEXT         Search by author; repeat for multiple authors
   --author-id ID        List or search books by author ID; repeat for multiple IDs
   --category ID|NAME    List or search within a category; repeat for multiple categories
   --field FIELD         title, author, category, author-id, author_id, or all
   --all                 Search title and author fields
   --exact               Require exact title/author matches
   --format FORMAT       Filter by format; repeat or use comma-separated values
   --limit N             Limit displayed results
   --page N              Listing page for category, author ID, and format searches

``show``
~~~~~~~~

.. code-block:: bash

   vnthuquan show --title "..." --links
   vnthuquan show --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --assets

``download``
~~~~~~~~~~~~

.. code-block:: bash

   vnthuquan download --title "..." --format epub --out ~/Downloads --dry-run
   vnthuquan download --title "..." --format epub --out ~/Downloads --execute
   vnthuquan download --title "..." --format pdf --out ~/Downloads --dry-run
   vnthuquan download --title "..." --format text --out ~/Downloads --execute
   vnthuquan download --title "..." --format audio --out ~/Downloads --dry-run
   vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --out ~/Downloads --execute
   vnthuquan download --id "2qtqv3m3237n..." --out ~/Downloads --manifest plan.json

Recommended format-specific workflow:

.. code-block:: bash

   vnthuquan search --format pdf --limit 5
   vnthuquan show --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --links
   vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format pdf --out ~/Downloads --dry-run
   vnthuquan download --url "http://vietnamthuquan.eu/truyen/truyen.aspx?tid=..." --format pdf --out ~/Downloads --execute

Download option summary:

.. code-block:: text

   --title TEXT       Resolve by title
   --url URL          Resolve by book URL
   --id TID           Resolve by site TID
   --format FORMAT    epub, pdf, text, or audio
   --out DIR          Output directory
   --index N          Select a title-search result when the title is ambiguous
   --exact            Require exact title match
   --dry-run          Show the plan without downloading
   --execute          Download and write files
   --strict-verify    Use stricter post-download validation
   --no-failover      Do not retry known mirrors after download failure
   --manifest PATH    Write a download manifest JSON file

Download output by format:

.. code-block:: text

   epub     direct .epub asset
   pdf      direct .pdf source exposed by the site reader
   text     generated UTF-8 .txt file from text chapters
   audio    .zip bundle containing MP3 files and manifest.json

``validate``
~~~~~~~~~~~~

.. code-block:: bash

   vnthuquan validate ~/Downloads/book.epub
   vnthuquan validate ~/Downloads/book.pdf --format pdf
   vnthuquan validate ~/Downloads/book.txt --format text
   vnthuquan validate ~/Downloads/book.zip --format audio
   vnthuquan validate ~/Downloads/book.zip --format audio --strict

``list``
~~~~~~~~

.. code-block:: bash

   vnthuquan list latest --page 1 --limit 10
   vnthuquan list authors --initial A --page 1
   vnthuquan list title-initial A --format epub --page 1
   vnthuquan list category 23 --format epub --page 1
   vnthuquan list author 284 --format epub --page 1
   vnthuquan list format epub --page 1 --limit 10
   vnthuquan list most-viewed --page 1 --limit 10
   vnthuquan list five-star --page 1 --limit 10
   vnthuquan list top --category 6 --source most-viewed --scan-pages 20 --limit 10
   vnthuquan list top --author-id 284 --source most-viewed --scan-pages 20 --limit 10

``list top`` is derived from global ranked lists. ``--scan-pages`` controls how
many ranked pages are fetched before local category or author filtering.

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
