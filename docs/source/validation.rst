Validation
==========

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

Validation can prove that a downloaded file is structurally usable and that the
HTTP transfer was not obviously truncated. It cannot prove that the ebook
matches a canonical edition unless an external source is checked separately.

``content_completeness`` defaults to ``unknown``.
