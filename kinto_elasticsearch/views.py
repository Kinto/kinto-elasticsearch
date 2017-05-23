import logging

import elasticsearch
from kinto.core import authorization
from kinto.core import Service
from kinto.core import utils


logger = logging.getLogger(__name__)


class RouteFactory(authorization.RouteFactory):
    def __init__(self, request):
        super().__init__(request)
        records_plural = utils.strip_uri_prefix(request.path.replace("/search", "/records"))
        self.permission_object_id = records_plural
        self.required_permission = "read"


search = Service(name="search",
                 path='/buckets/{bucket_id}/collections/{collection_id}/search',
                 description="Search",
                 factory=RouteFactory)


@search.post(permission=authorization.DYNAMIC)
def get_search(request):
    bucket_id = request.matchdict['bucket_id']
    if bucket_id == "default":
        try:
            bucket_id = request.default_bucket_id
        except AttributeError as e:  # pragma: no cover
            pass  # `default` bucket without default_bucket plugin.

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
