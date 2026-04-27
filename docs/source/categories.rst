Categories And Formats
======================

Category, author ID, and format support is read-only, but it can be used for
search and listing. These selectors use the site's paginated listing pages, so
``--page`` controls which page is fetched.

.. code-block:: bash

   vnthuquan categories list
   vnthuquan categories show 23
   vnthuquan formats list
   vnthuquan list category 23 --format epub --page 1
   vnthuquan list format epub --page 1 --limit 10
   vnthuquan search --category 23 --category 26 --format epub --page 1
   vnthuquan search --author-id 42 --author-id 1600 --format epub --page 1
   vnthuquan search --format pdf,epub --page 1 --limit 10

Format IDs:

.. code-block:: text

   text   0
   image  1
   pdf    2
   audio  3
   epub   4

Repeated categories and author IDs are OR filters. Formats can be repeated or
comma-separated. Category + format and author ID + format filtering are
supported for search/listing. Bulk category downloads are deferred.
