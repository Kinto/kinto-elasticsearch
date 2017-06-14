import copy
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


class PostActivation(BaseWebTest, unittest.TestCase):

    @classmethod
    def get_app_settings(cls, extras=None):
        settings = super().get_app_settings(extras)
        settings['storage_backend'] = 'kinto.core.storage.postgresql'
        settings['storage_url'] = 'postgres://postgres:postgres@localhost:5432/postgres'
        settings['permission_backend'] = 'kinto.core.permission.postgresql'
        settings['permission_url'] = settings['storage_url']
        return settings

    def setUp(self):
        app = self.make_app(settings={"kinto.includes": ""})
        capabilities = app.get("/").json["capabilities"]
        assert "elasticsearch" not in capabilities

        app.put("/buckets/bid", headers=self.headers)
        app.put("/buckets/bid/collections/cid", headers=self.headers)
        app.post_json("/buckets/bid/collections/cid/records",
                      {"data": {"before": "indexing"}},
                      headers=self.headers)

    def test_search_does_not_fail(self):
        resp = self.app.get("/buckets/bid/collections/cid/records",
                            headers=self.headers)
        assert len(resp.json["data"]) == 1

        resp = self.app.get("/buckets/bid/collections/cid/search",
                            headers=self.headers)
        results = resp.json
        assert len(results["hits"]["hits"]) == 0

    def test_record_creation_does_not_fail(self):
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"after": "indexing"}},
                           headers=self.headers)

        resp = self.app.get("/buckets/bid/collections/cid/search",
                            headers=self.headers)
        results = resp.json
        assert len(results["hits"]["hits"]) == 1
        assert results["hits"]["hits"][0]["_source"]["after"] == "indexing"


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


class LimitedResults(BaseWebTest, unittest.TestCase):
    def get_app(self, settings):
        app = self.make_app(settings=settings)
        app.put("/buckets/bid", headers=self.headers)
        app.put("/buckets/bid/collections/cid", headers=self.headers)
        requests = [{
            "method": "POST",
            "path": "/buckets/bid/collections/cid/records",
            "body": {"data": {"age": i}}
        } for i in range(5)]
        app.post_json("/batch", {"requests": requests}, headers=self.headers)
        return app

    def test_the_number_of_responses_is_limited_by_paginate_by_setting(self):
        app = self.get_app({"paginate_by": 2})
        resp = app.get("/buckets/bid/collections/cid/search", headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 2

    def test_the_number_of_responses_is_limited_by_max_fetch_size_setting(self):
        app = self.get_app({"storage_max_fetch_size": 2})
        resp = app.get("/buckets/bid/collections/cid/search", headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 2

    def test_the_number_of_responses_is_limited_by_smaller_limit(self):
        app = self.get_app({"paginate_by": 4, "storage_max_fetch_size": 2})
        resp = app.get("/buckets/bid/collections/cid/search", headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 2

    def test_the_number_of_responses_is_limited_by_only_defined_limit(self):
        app = self.get_app({"paginate_by": 0, "storage_max_fetch_size": 2})
        resp = app.get("/buckets/bid/collections/cid/search", headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 2

    def test_size_specified_in_query_is_taken_into_account(self):
        app = self.get_app({"paginate_by": 3})
        query = {
            "from": 0, "size" : 2,
            "query": {"match_all": {}}
        }
        resp = app.post_json("/buckets/bid/collections/cid/search", query,
                             headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 2

    def test_size_specified_in_query_is_caped_by_setting(self):
        app = self.get_app({"paginate_by": 3})
        query = {
            "size" : 4,
            "query": {"match_all": {}}
        }
        resp = app.post_json("/buckets/bid/collections/cid/search", query,
                             headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 3


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


class SchemaSupport(BaseWebTest, unittest.TestCase):

    schema = {
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

    def setUp(self):
        self.app.put("/buckets/bid", headers=self.headers)
        body = {"data": {"index:schema": self.schema}}
        self.app.put_json("/buckets/bid/collections/cid", body, headers=self.headers)
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"build": {"id": "abc", "date": "2017-05-24"}}},
                           headers=self.headers)
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"build": {"id": "efg", "date": "2017-02-01"}}},
                           headers=self.headers)

    def get_mapping(self, bucket_id, collection_id):
        indexer = self.app.app.registry.indexer
        indexname = indexer.indexname(bucket_id, collection_id)
        index_mapping = indexer.client.indices.get_mapping(indexname)
        mappings = index_mapping[indexname]["mappings"]
        return mappings.get(indexname, {})

    def test_index_has_mapping_if_collection_has_schema(self):
        mapping = self.get_mapping("bid", "cid")
        assert sorted(mapping["properties"].keys()) == ["build", "id", "last_modified"]

    def test_mapping_is_updated_on_collection_update(self):
        new_schema = copy.deepcopy(self.schema)
        new_schema["properties"]["build"]["properties"]["id"]["ignore_above"] = 12

        self.app.patch_json("/buckets/bid/collections/cid",
                            {"data": {"index:schema": new_schema}},
                            headers=self.headers)

        mapping = self.get_mapping("bid", "cid")
        assert mapping["properties"]["build"]["properties"]["id"]["ignore_above"] == 12

    def test_mapping_is_created_when_index_metadata_is_added(self):
        self.app.put("/buckets/bid/collections/cid2", headers=self.headers)
        mapping = self.get_mapping("bid", "cid2")
        assert "build" not in mapping.get("properties", {})

        self.app.patch_json("/buckets/bid/collections/cid2",
                            {"data": {"index:schema": self.schema}},
                            headers=self.headers)

        mapping = self.get_mapping("bid", "cid2")
        assert "build" in mapping["properties"]

    def test_mapping_is_preserved_when_index_metadata_is_removed(self):
        self.app.put_json("/buckets/bid/collections/cid",
                          {"data": {}},
                          headers=self.headers)

        mapping = self.get_mapping("bid", "cid")
        assert "build" in mapping["properties"]

    def test_can_search_for_subproperties(self):
        body = {
            "query": {
                "bool" : {
                    "must" : {
                        "term" : { "build.id" : "abc" }
                    }
                }
            }
        }
        resp = self.app.post_json("/buckets/bid/collections/cid/search", body,
                                  headers=self.headers)
        result = resp.json
        assert len(result["hits"]["hits"]) == 1
        assert result["hits"]["hits"][0]["_source"]["build"]["id"] == "abc"

    def test_can_aggregate_values(self):
        body = {
          "aggs" : {
            "build_dates" : {
              "terms": {
                "field" : "build.id",
                "size" : 1000
              }
            }
          }
        }
        resp = self.app.post_json("/buckets/bid/collections/cid/search", body,
                                  headers=self.headers)
        result = resp.json
        assert result["aggregations"]["build_dates"]["buckets"] == [
            {"key": "abc", "doc_count": 1},
            {"key": "efg", "doc_count": 1},
        ]

    def test_search_parse_exception_returns_400(self):
        e = elasticsearch.RequestError('', '',
                                       {"error": "Could not find aggregator type"})
        with mock.patch("kinto_elasticsearch.indexer.Indexer.search",
                        side_effect=e):
            self.app.post_json("/buckets/bid/collections/cid/search",
                               headers=self.headers, status=400)
