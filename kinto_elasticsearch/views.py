import logging

import elasticsearch
from kinto.core import Service


logger = logging.getLogger(__name__)

search = Service(name="search",
                 path='/buckets/{bucket_id}/collections/{collection_id}/search',
                 description="Search")


@search.post()
def get_search(request):
    bucket_id = request.matchdict['bucket_id']
    collection_id = request.matchdict['collection_id']

    query = request.body

    # Access indexer from views using registry.
    indexer = request.registry.indexer
    try:
        results = indexer.search(bucket_id, collection_id, query)
    except elasticsearch.ElasticsearchException as e:
        logger.exception("Index query failed.")
        results = {}
    return results
