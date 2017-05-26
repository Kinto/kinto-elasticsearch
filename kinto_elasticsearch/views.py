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


def search_view(request, **kwargs):
    bucket_id = request.matchdict['bucket_id']
    collection_id = request.matchdict['collection_id']

    # Access indexer from views using registry.
    indexer = request.registry.indexer
    try:
        results = indexer.search(bucket_id, collection_id, **kwargs)
    except elasticsearch.ElasticsearchException as e:
        logger.exception("Index query failed.")
        results = {}
    return results


@search.post(permission=authorization.DYNAMIC)
def post_search(request):
    body = request.body
    return search_view(request, body=body)


@search.get(permission=authorization.DYNAMIC)
def get_search(request):
    q = request.GET.get("q")
    return search_view(request, q=q)
