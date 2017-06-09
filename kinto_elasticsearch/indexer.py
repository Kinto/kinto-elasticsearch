import logging
from contextlib import contextmanager

import elasticsearch
import elasticsearch.helpers
from pyramid.settings import aslist, asbool


logger = logging.getLogger(__name__)


class Indexer(object):
    def __init__(self, hosts, prefix="kinto", force_refresh=False):
        self.client = elasticsearch.Elasticsearch(hosts)
        self.prefix = prefix
        self.force_refresh = force_refresh

    def indexname(self, bucket_id, collection_id):
        return "{}-{}-{}".format(self.prefix, bucket_id, collection_id)

    def create_index(self, bucket_id, collection_id, schema=None):
        indexname = self.indexname(bucket_id, collection_id)
        # Only if necessary.
        if not self.client.indices.exists(index=indexname):
            if schema:
                body = {"mappings": {indexname: schema}}
            else:
                body = None
            return self.client.indices.create(index=indexname, body=body)
        else:
            return self.update_index(bucket_id, collection_id, schema)

    def update_index(self, bucket_id, collection_id, schema=None):
        indexname = self.indexname(bucket_id, collection_id)
        if schema is None:
            schema = {"properties": {}}
        self.client.indices.put_mapping(index=indexname,
                                        doc_type=indexname,
                                        body=schema)

    def delete_index(self, bucket_id, collection_id=None):
        if collection_id is None:
            collection_id = "*"
        indexname = self.indexname(bucket_id, collection_id)
        try:
            return self.client.indices.delete(index=indexname)
        except elasticsearch.exceptions.NotFoundError:  # pragma: no cover
            pass

    def search(self, bucket_id, collection_id, **kwargs):
        indexname = self.indexname(bucket_id, collection_id)
        return self.client.search(index=indexname,
                                  doc_type=indexname,
                                  **kwargs)

    def flush(self):
        self.client.indices.delete(index="{}-*".format(self.prefix))

    @contextmanager
    def bulk(self):
        bulk = BulkClient(self)
        yield bulk
        elasticsearch.helpers.bulk(self.client,
                                   bulk.operations,
                                   refresh=self.force_refresh)


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
    prefix = settings.get('elasticsearch.index_prefix', 'kinto')
    force_refresh = asbool(settings.get('elasticsearch.force_refresh', 'false'))
    indexer = Indexer(hosts=hosts, prefix=prefix, force_refresh=force_refresh)
    return indexer
