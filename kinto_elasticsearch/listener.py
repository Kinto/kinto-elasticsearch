import logging

import elasticsearch
from elasticsearch import helpers
from kinto.core.events import ACTIONS


logger = logging.getLogger(__name__)


def on_record_changed(event):
    indexer = event.request.registry.indexer

    bucket_id = event.payload["bucket_id"]
    collection_id = event.payload["collection_id"]
    action = event.payload["action"]

    try:
        with indexer.bulk() as bulk:
            for change in event.impacted_records:
                if action == ACTIONS.DELETE.value:
                    bulk.unindex_record(bucket_id,
                                        collection_id,
                                        record=change["old"],
                                        id_field="id")
                else:
                    bulk.index_record(bucket_id,
                                      collection_id,
                                      record=change["new"],
                                      id_field="id")
    except elasticsearch.ElasticsearchException:
        logger.exception("Failed to index record")


def on_server_flushed(event):
    indexer = event.request.registry.indexer
    indexer.flush()
