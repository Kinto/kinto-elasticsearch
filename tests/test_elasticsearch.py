import mock
import time
import unittest

import elasticsearch
from kinto.core import utils as core_utils
from kinto.core.testing import get_user_headers

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
        assert expected == capabilities['elasticsearch']

    def test_indexer_flush(self):
        with mock.patch("kinto_elasticsearch.indexer.Indexer.flush") as flush:
            self.app.post("/__flush__", status=202)
            assert flush.called

    def test_present_in_heartbeat(self):
        resp = self.app.get("/__heartbeat__")
        assert "elasticsearch" in resp.json

    def test_returns_false_if_connection_fails(self):
        with mock.patch("kinto_elasticsearch.indexer.elasticsearch.Elasticsearch.ping",
                        side_effect=ValueError):
            resp = self.app.get("/__heartbeat__", status=503)
            assert not resp.json["elasticsearch"]


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

    def test_deleted_records_are_unindexed(self):
        rid = self.record["id"]
        self.app.delete("/buckets/bid/collections/cid/records/{}".format(rid),
                        headers=self.headers)
        resp = self.app.post("/buckets/bid/collections/cid/search",
                             headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 0

    def test_response_is_served_if_indexer_fails(self):
        with mock.patch("kinto_elasticsearch.indexer.elasticsearch.helpers.bulk",
                        side_effect=elasticsearch.ElasticsearchException):
            r = self.app.post_json("/buckets/bid/collections/cid/records",
                                   {"data": {"hola": "mundo"}},
                                   headers=self.headers)
            assert r.status_code == 201


class ParentDeletion(BaseWebTest, unittest.TestCase):

    def setUp(self):
        self.app.put("/buckets/bid", headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)
        resp = self.app.post_json("/buckets/bid/collections/cid/records",
                                  {"data": {"hello": "world"}},
                                  headers=self.headers)

    def index_exists(self, bucket_id, collection_id):
        indexer = self.app.app.registry.indexer
        indexname = indexer.indexname(bucket_id, collection_id)
        return indexer.client.indices.exists(indexname)

    def test_index_is_deleted_when_collection_is_deleted(self):
        self.app.delete("/buckets/bid/collections/cid", headers=self.headers)
        assert not self.index_exists("bid", "cid")

    def test_index_is_deleted_when_bucket_is_deleted(self):
        self.app.delete("/buckets/bid", headers=self.headers)
        assert not self.index_exists("bid", "cid")


class SearchView(BaseWebTest, unittest.TestCase):
    def setUp(self):
        self.app.put("/buckets/bid", headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)

    def test_search_response_is_empty_if_indexer_fails(self):
        with mock.patch("kinto_elasticsearch.indexer.Indexer.search",
                        side_effect=elasticsearch.ElasticsearchException):
            resp = self.app.post("/buckets/bid/collections/cid/search",
                                 headers=self.headers)
            result = resp.json
            assert result == {}

    def test_invalid_search_query(self):
        body = {"whatever": {"wrong": "bad"}}
        resp = self.app.post_json("/buckets/bid/collections/cid/search",
                                  body,
                                  headers=self.headers,
                                  status=400)
        assert resp.json["message"] == "Unknown key for a START_OBJECT in [whatever]."
        assert resp.json["details"] == {
            "col": 14,
            "line": 1,
            "reason": "Unknown key for a START_OBJECT in [whatever].",
            "type": "parsing_exception"
        }

    def test_search_on_empty_collection_returns_empty_list(self):
        resp = self.app.post("/buckets/bid/collections/cid/search",
                             headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 0

    def test_querystring_search_is_supported(self):
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"age": 12}}, headers=self.headers)
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"age": 21}}, headers=self.headers)
        resp = self.app.get("/buckets/bid/collections/cid/search?q=age:<15",
                             headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 1
        assert result["hits"]["hits"][0]["_source"]["age"] == 12

    def test_empty_querystring_returns_all_results(self):
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"age": 12}}, headers=self.headers)
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"age": 21}}, headers=self.headers)
        resp = self.app.get("/buckets/bid/collections/cid/search",
                             headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 2


class PermissionsCheck(BaseWebTest, unittest.TestCase):
    def test_search_is_allowed_if_write_on_bucket(self):
        body = {"permissions": {"write": ["system.Everyone"]}}
        self.app.put_json("/buckets/bid", body, headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)

        self.app.post("/buckets/bid/collections/cid/search", status=200)

    def test_search_is_allowed_if_read_on_bucket(self):
        body = {"permissions": {"read": ["system.Everyone"]}}
        self.app.put_json("/buckets/bid", body, headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)

        self.app.post("/buckets/bid/collections/cid/search", status=200)

    def test_search_is_allowed_if_write_on_collection(self):
        self.app.put("/buckets/bid", headers=self.headers)
        body = {"permissions": {"write": ["system.Everyone"]}}
        self.app.put_json("/buckets/bid/collections/cid", body, headers=self.headers)

        self.app.post("/buckets/bid/collections/cid/search", status=200)

    def test_search_is_allowed_if_read_on_collection(self):
        self.app.put("/buckets/bid", headers=self.headers)
        body = {"permissions": {"read": ["system.Everyone"]}}
        self.app.put_json("/buckets/bid/collections/cid", body, headers=self.headers)

        self.app.post("/buckets/bid/collections/cid/search", status=200)

    def test_search_is_not_allowed_by_default(self):
        self.app.put("/buckets/bid", headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)

        self.app.post("/buckets/bid/collections/cid/search", status=401)
        headers = get_user_headers("cual", "quiera")
        self.app.post("/buckets/bid/collections/cid/search", status=403, headers=headers)

    def test_search_is_not_allowed_if_only_read_on_certain_records(self):
        self.app.put("/buckets/bid", headers=self.headers)
        body = {"permissions": {"record:create": ["system.Authenticated"]}}
        self.app.put_json("/buckets/bid/collections/cid", body, headers=self.headers)
        headers = get_user_headers("toto")
        self.app.post_json("/buckets/bid/collections/cid/records", {"data": {"pi": 42}},
                           headers=headers)

        self.app.post("/buckets/bid/collections/cid/search", status=403, headers=headers)
