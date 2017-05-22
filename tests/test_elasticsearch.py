import mock
import time
import unittest

import elasticsearch
from kinto.core import utils as core_utils

from kinto_elasticsearch import __version__ as elasticsearch_version
from . import BaseWebTest


class PluginSetup(BaseWebTest, unittest.TestCase):

    def test_elasticsearch_capability_exposed(self):
        resp = self.app.get('/')
        capabilities = resp.json['capabilities']
        self.assertIn('elasticsearch', capabilities)
        expected = {
            "version": elasticsearch_version,
            "description": "Index and search records using ElasticSearch.",
            "url": "https://github.com/Kinto/kinto-elasticsearch"
        }
        self.assertEqual(expected, capabilities['elasticsearch'])


class RecordIndexing(BaseWebTest, unittest.TestCase):

    def setUp(self):
        self.app.put("/buckets/bid", headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)
        resp = self.app.post_json("/buckets/bid/collections/cid/records",
                                  {"data": {"hello": "world"}},
                                  headers=self.headers)
        self.record = resp.json["data"]

    def test_new_records_are_indexed(self):
        resp = self.app.post("/buckets/bid/collections/cid/search",
                             headers=self.headers)
        result = resp.json
        assert result["hits"]["hits"][0]["_source"] == self.record

    def test_new_records_are_indexed(self):
        rid = self.record["id"]
        self.app.delete("/buckets/bid/collections/cid/records/{}".format(rid),
                        headers=self.headers)
        resp = self.app.post("/buckets/bid/collections/cid/search",
                             headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 0

    def test_response_is_served_if_indexer_fails(self):
        with mock.patch("kinto_elasticsearch.indexer.elasticsearch.Elasticsearch.index",
                        side_effect=elasticsearch.ElasticsearchException):
            r = self.app.post_json("/buckets/bid/collections/cid/records",
                                   {"data": {"hola": "mundo"}},
                                   headers=self.headers)
            assert r.status_code == 201


class SearchView(BaseWebTest, unittest.TestCase):
    def test_search_response_is_empty_if_indexer_fails(self):
        with mock.patch("kinto_elasticsearch.indexer.Indexer.search",
                        side_effect=elasticsearch.ElasticsearchException):
            resp = self.app.post("/buckets/bid/collections/cid/search",
                                 headers=self.headers)
            result = resp.json
            assert result == {}
