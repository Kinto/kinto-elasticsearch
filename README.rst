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

    $ echo '{"data": {"note": "kinto"}}' | http POST http://localhost:8888/v1/buckets/example/collections/notes/records --auth token:alice-token --verbose


It should now be possible to search for it:

::

    $ http POST http://localhost:8888/v1/buckets/default/collections/assets/search --auth token:alice-token --verbose

.. code-block:: http
    :emphasize-lines: 20-24

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


Running the tests
=================

::

  $ make tests
