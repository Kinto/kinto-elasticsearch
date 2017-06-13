Changelog
=========


0.2.0 (2017-06-13)
------------------

**Bug fixes**

- Limit the number of results returned by default (fixes #45)
- Fix crash on search parse exceptions (fixes #44)


0.1.0 (2017-05-26)
------------------

**New features**

- Flush indices when server is flushed (fixes #4)
- Perform insertions and deletion in bulk for better efficiency (fixes #5)
- Add setting to force index refresh on change (fixes #6)
- Add heartbeat (fixes #3)
- Delete indices when buckets and collections are deleted (fixes #21)
- Support quick search from querystring (fixes #34)
- Return details about invalid queries in request body (fixes #23)
- Support defining mapping from the ``index:schema`` property in the collection metadata (ref #8)

**Bug fixes**

- Only index records if the storage transaction is committed (fixes #15)
- Do not allow to search if no read permission on collection or bucket (fixes #7)
- Fix empty results response when plugin was enabled after collection creation (ref #20)

**Internal changes**

- Create index when collection is created (fixes #27)


0.0.1 (2017-05-22)
------------------

- Import code from `Kinto official tutorial <http://kinto.readthedocs.io/en/stable/tutorials/write-plugin.html>`_
