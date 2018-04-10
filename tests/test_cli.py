import elasticsearch
import mock
import os
import unittest
from kinto_elasticsearch.command_reindex import main, reindex_records, get_paginated_records
from . import BaseWebTest

HERE = os.path.abspath(os.path.dirname(__file__))


class TestMain(BaseWebTest, unittest.TestCase):

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

    def test_cli_fail_if_elasticsearch_plugin_not_installed(self):
        with mock.patch('kinto_elasticsearch.command_reindex.logger') as logger:
            exit_code = main(['--ini', os.path.join(HERE, 'wrong_config.ini'),
                              '--bucket', 'bid', '--collection', 'cid'])
            assert exit_code == 62
            logger.error.assert_called_with('kinto-elasticsearch not available.')

    def test_cli_fail_if_collection_or_bucket_do_not_exists(self):
        with mock.patch('kinto_elasticsearch.command_reindex.logger') as logger:
            exit_code = main(['--ini', os.path.join(HERE, 'config.ini'),
                              '--bucket', 'bid', '--collection', 'cid'])
            assert exit_code == 63
            logger.error.assert_called_with(
                "No collection 'cid' in bucket 'bid'")

    def test_cli_fail_if_collection_has_no_index_schema(self):
        # Create collection or bucket
        self.app.put("/buckets/bid", headers=self.headers)
        self.app.put("/buckets/bid/collections/cid", headers=self.headers)

        with mock.patch('kinto_elasticsearch.command_reindex.logger') as logger:
            exit_code = main(['--ini', os.path.join(HERE, 'config.ini'),
                              '--bucket', 'bid', '--collection', 'cid'])
            assert exit_code == 64
            logger.error.assert_called_with(
                'No `index:schema` attribute found in collection metadata.')

    def test_cli_reindexes_if_collection_has_an_index_schema(self):
        # Create collection or bucket
        self.app.put("/buckets/bid", headers=self.headers)
        body = {"data": {"index:schema": self.schema}}
        self.app.put_json("/buckets/bid/collections/cid", body, headers=self.headers)
        self.app.post_json("/buckets/bid/collections/cid/records",
                           {"data": {"build": {"id": "efg", "date": "2017-02-01"}}},
                           headers=self.headers)

        exit_code = main(['--ini', os.path.join(HERE, 'config.ini'),
                          '--bucket', 'bid', '--collection', 'cid'])
        assert exit_code == 0

    def test_cli_logs_elasticsearch_exceptions(self):
        indexer = mock.MagicMock()
        indexer.bulk().__enter__().index_record.side_effect = elasticsearch.ElasticsearchException

        with mock.patch('kinto_elasticsearch.command_reindex.logger') as logger:
            with mock.patch('kinto_elasticsearch.command_reindex.get_paginated_records',
                            return_value=[[{}, {}]]) as get_paginated_records:
                reindex_records(indexer,
                                mock.sentinel.storage,
                                mock.sentinel.bucket_id,
                                mock.sentinel.collection_id)
                get_paginated_records.assert_called_with(mock.sentinel.storage,
                                                         mock.sentinel.bucket_id,
                                                         mock.sentinel.collection_id)
                logger.exception.assert_called_with('Failed to index record')

    def test_cli_default_to_sys_argv(self):
        with mock.patch('sys.argv', ['cli', '--ini', os.path.join(HERE, 'wrong_config.ini')]):
            exit_code = main()
            assert exit_code == 62

    def test_get_paginated_records(self):
        # Create collection or bucket
        self.app.put("/buckets/bid", headers=self.headers)
        body = {"data": {"index:schema": self.schema}}
        self.app.put_json("/buckets/bid/collections/cid", body, headers=self.headers)
        for i in range(5):
            self.app.post_json("/buckets/bid/collections/cid/records",
                               {"data": {"build": {"id": "efg%d" % i, "date": "2017-02-01"}}},
                               headers=self.headers)
        page_count = 0
        for records in get_paginated_records(self.app.app.registry.storage, 'bid', 'cid', limit=3):
            page_count += 1
        assert page_count == 2
