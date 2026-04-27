Validation
==========

Supported validators
--------------------

EPUB validation checks:

* byte count when an expected size is known
* SHA256
* ZIP integrity
* ``mimetype`` equals ``application/epub+zip``
* ``META-INF/container.xml`` exists
* OPF package exists
* manifest and spine files exist
* readable content documents
* TOC/nav presence is reported
* demo/sample markers are scanned heuristically

PDF validation checks:

* byte count when an expected size is known
* SHA256
* PDF header
* PDF EOF marker when present near the end of the file
* readable non-empty payload

Text validation checks:

* SHA256
* valid UTF-8
* readable text length
* demo/sample markers are scanned heuristically

Audio validation checks:

* SHA256
* ZIP integrity for audio bundles
* at least one MP3 entry
* MP3 header check for every audio entry

Strict validation
-----------------

``vnthuquan validate --strict`` and ``vnthuquan download --strict-verify`` turn
selected structural warnings into errors:

* EPUB requires a TOC/nav item and fails on demo/sample markers.
* PDF requires an EOF marker near the end of the file.
* Text fails on HTML-looking output or demo/sample markers.
* Audio ZIP bundles require a valid ``manifest.json`` whose entries match the
  bundled MP3 files.

External validation
-------------------

External validators are optional and run only when requested:

.. code-block:: bash

   vnthuquan validate book.epub --external
   vnthuquan validate book.epub --epubcheck
   vnthuquan validate book.epub --ace
   vnthuquan download --title "..." --format epub --execute --epubcheck

For EPUB files, ``--external`` selects ``epubcheck`` and Ace by DAISY. Missing
executables are reported as validation failures because the user explicitly
requested the external check.

Format limits
-------------

Validation is structural, not bibliographic:

* EPUB validation checks package structure and readable spine documents.
* PDF validation checks the file looks like a readable PDF transfer.
* Text validation checks the generated export is readable UTF-8 text.
* Audio validation checks the ZIP bundle and MP3 headers.

Validation can prove that a downloaded file is structurally usable and that the
HTTP transfer was not obviously truncated. For generated text exports, it can
only prove that the exported file is readable UTF-8 text; it cannot prove that
the source site has every canonical chapter. Validation cannot prove that the
ebook matches a canonical edition unless an external source is checked
separately.

``content_completeness`` defaults to ``unknown``.
