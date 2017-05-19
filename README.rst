===================
Kinto ElasticSearch
===================

.. image:: https://img.shields.io/travis/Kinto/kinto-elasticsearch.svg
        :target: https://travis-ci.org/Kinto/kinto-elasticsearch

.. image:: https://img.shields.io/pypi/v/kinto-elasticsearch.svg
        :target: https://pypi.python.org/pypi/kinto-elasticsearch

.. image:: https://coveralls.io/repos/Kinto/kinto-elasticsearch/badge.svg?branch=master
        :target: https://coveralls.io/r/Kinto/kinto-elasticsearch

**kinto-elasticsearch** forwards the records to ElasticSearch and provides a ``/search``
endpoint to query the indexed data.


Install
-------

::

    pip install kinto-elasticsearch

Setup
-----

In the `Kinto <http://kinto.readthedocs.io/>`_ settings:

.. code-block :: ini

    kinto.includes = kinto_elasticsearch
    kinto.elasticsearch.hosts = localhost:9200
