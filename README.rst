Kinto ElasticSearch
###################

.. image:: https://img.shields.io/travis/Kinto/kinto-elasticsearch.svg
        :target: https://travis-ci.org/Kinto/kinto-elasticsearch

.. image:: https://img.shields.io/pypi/v/kinto-elasticsearch.svg
        :target: https://pypi.python.org/pypi/kinto-elasticsearch

.. image:: https://coveralls.io/repos/Kinto/kinto-elasticsearch/badge.svg?branch=master
        :target: https://coveralls.io/r/Kinto/kinto-elasticsearch

**kinto-elasticsearch** forwards the records to ElasticSearch and provides a ``/search``
endpoint to query the indexed data.


Install
=======

::

    pip install kinto-elasticsearch


Setup
=====

In the `Kinto <http://kinto.readthedocs.io/>`_ settings:

.. code-block :: ini

    kinto.includes = kinto_elasticsearch
    kinto.elasticsearch.hosts = localhost:9200

By default, ElasticSearch is smart and indices are not refreshed on every change.
You can force this (with a certain drawback in performance):

.. code-block :: ini

    kinto.elasticsearch.force_refresh = true

By default, indices names are prefixed with ``kinto-``. You change this with:

.. code-block :: ini

    kinto.elasticsearch.index_prefix = myprefix


Run ElasticSearch
=================

Running a local install of *ElasticSearch* on ``localhost:9200`` with Docker is pretty straightforward:

::

    sudo docker run -p 9200:9200 elasticsearch

It is also be installed manually on Ubuntu with:

::

    sudo apt-get install elasticsearch

And more information is available in the `official docs <https://www.elastic.co/downloads/elasticsearch>`_.


Usage
=====

Create a new record:

::

    $ echo '{"data": {"note": "kinto"}}' | http POST http://localhost:8888/v1/buckets/example/collections/notes/records --auth token:alice-token


It should now be possible to search for it using the `ElasticSearch API <https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html>`_.

For example, using a quick querystring search:

::

    $ http "http://localhost:8888/v1/buckets/example/collections/notes/search?q=note:kinto"--auth token:alice-token


Or an advanced search using request body:

::

    $ echo '{"query": {"match_all": {}}}' | http POST http://localhost:8888/v1/buckets/example/collections/notes/search --auth token:alice-token

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 333
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 20 Jan 2016 12:02:05 GMT
    Server: waitress

    {
        "_shards": {
            "failed": 0,
            "successful": 5,
            "total": 5
        },
        "hits": {
            "hits": [
                {
                    "_id": "453ff779-e967-4b08-99b9-5c16af865a67",
                    "_index": "example-assets",
                    "_score": 1.0,
                    "_source": {
                        "id": "453ff779-e967-4b08-99b9-5c16af865a67",
                        "last_modified": 1453291301729,
                        "note": "kinto"
                    },
                    "_type": "example-assets"
                }
            ],
            "max_score": 1.0,
            "total": 1
        },
        "timed_out": false,
        "took": 20
    }


Custom index mapping
--------------------

By default, ElasticSearch infers the data types from the indexed records.

But it's possible to define the index mappings (ie. schema) from the collection metadata,
in the ``index:schema`` property:

.. code-block:: bash

    $ echo '{
      "data": {
        "index:schema": {
          "properties": {
            "id": {"type": "keyword"},
            "last_modified": {"type": "long"},
            "build": {
              "properties": {
                  "date": {"type": "date", "format": "strict_date"},
                  "id": {"type": "keyword"}
              }
            }
          }
        }
      }
    }' | http PATCH "http://localhost:8888/v1/buckets/blog/collections/builds" --auth token:admin-token --verbose

Refer to ElasticSearch official documentation for more information about mappings.

See also, `domapping <https://github.com/inveniosoftware/domapping/>`_ a CLI tool to convert JSON schemas to ElasticSearch mappings.


Running the tests
=================

::

  $ make tests
