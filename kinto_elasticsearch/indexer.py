import logging

import elasticsearch

from pyramid.settings import aslist


logger = logging.getLogger(__name__)


class Indexer(object):
    def __init__(self, hosts):
        self.client = elasticsearch.Elasticsearch(hosts)

    def search(self, bucket_id, collection_id, query, **kwargs):
        indexname = '%s-%s' % (bucket_id, collection_id)
        return self.client.search(index=indexname,
                                  doc_type=indexname,
                                  body=query,
                                  **kwargs)

    def index_record(self, bucket_id, collection_id, record, id_field):
        indexname = '%s-%s' % (bucket_id, collection_id)
        record_id = record[id_field]

        if not self.client.indices.exists(index=indexname):
            self.client.indices.create(index=indexname)

        index = self.client.index(index=indexname,
                                  doc_type=indexname,
                                  id=record_id,
                                  body=record,
                                  refresh=True)
        return index

    def unindex_record(self, bucket_id, collection_id, record, id_field):
        indexname = '%s-%s' % (bucket_id, collection_id)
        record_id = record[id_field]
        result = self.client.delete(index=indexname,
                                    doc_type=indexname,
                                    id=record_id,
                                    refresh=True)
        return result


def load_from_config(config):
    settings = config.get_settings()
    hosts = aslist(settings.get('elasticsearch.hosts', 'localhost:9200'))
    indexer = Indexer(hosts=hosts)
    return indexer
