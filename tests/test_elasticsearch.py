import mock
import time
import unittest

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

    def test_new_records_are_indexed(self):
        resp = self.app.post_json("/buckets/bid/collections/cid/records",
                                  {"data": {"hello": "world"}},
                                  headers=self.headers)
        record = resp.json["data"]

        resp = self.app.post("/buckets/bid/collections/cid/search",
                             headers=self.headers)
        result = resp.json
        print(result["hits"]["hits"])
        assert result["hits"]["hits"][0]["_source"] == record
