import logging
from contextlib import contextmanager

import elasticsearch
import elasticsearch.helpers
from pyramid.settings import aslist


logger = logging.getLogger(__name__)


class Indexer(object):
    def __init__(self, hosts, prefix="kinto"):
        self.client = elasticsearch.Elasticsearch(hosts)
        self.prefix = prefix

    def indexname(self, bucket_id, collection_id):
        return "{}-{}-{}".format(self.prefix, bucket_id, collection_id)

    def search(self, bucket_id, collection_id, query, **kwargs):
        indexname = self.indexname(bucket_id, collection_id)
        return self.client.search(index=indexname,
                                  doc_type=indexname,
                                  body=query,
                                  **kwargs)

    def flush(self):
        self.client.indices.delete(index="{}-*".format(self.prefix))

    @contextmanager
    def bulk(self):
        bulk = BulkClient(self)
        yield bulk
        elasticsearch.helpers.bulk(self.client, bulk.operations)


class BulkClient:
    def __init__(self, indexer):
        self.indexer = indexer
        self.operations = []

    def index_record(self, bucket_id, collection_id, record, id_field):
        indexname = self.indexer.indexname(bucket_id, collection_id)
        record_id = record[id_field]
        self.operations.append({
            '_op_type': 'index',
            '_index': indexname,
            '_type': indexname,
            '_id': record_id,
            '_source': record,
        })

    def unindex_record(self, bucket_id, collection_id, record, id_field):
        indexname = self.indexer.indexname(bucket_id, collection_id)
        record_id = record[id_field]
        self.operations.append({
            '_op_type': 'delete',
            '_index': indexname,
            '_type': indexname,
            '_id': record_id,
        })


def heartbeat(request):
    """Test that ElasticSearch is operationnal.

    :param request: current request object
    :type request: :class:`~pyramid:pyramid.request.Request`
    :returns: ``True`` is everything is ok, ``False`` otherwise.
    :rtype: bool
    """
    indexer = request.registry.indexer
    try:
        return indexer.client.ping()
    except Exception as e:
        logger.exception(e)
        return False


def load_from_config(config):
    settings = config.get_settings()
    hosts = aslist(settings.get('elasticsearch.hosts', 'localhost:9200'))
    indexer = Indexer(hosts=hosts)
    return indexer
