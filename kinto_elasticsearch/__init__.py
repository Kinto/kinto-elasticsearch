import pkg_resources

from kinto.events import ServerFlushed
from kinto.core.events import AfterResourceChanged

from . import indexer
from . import listener


#: Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version


def includeme(config):
    # Register a global indexer object
    config.registry.indexer = indexer.load_from_config(config)

    # Register heartbeat to check elasticsearch integration.
    config.registry.heartbeats["elasticsearch"] = indexer.heartbeat

    # Activate end-points.
    config.scan("kinto_elasticsearch.views")

    config.add_subscriber(listener.on_record_changed, AfterResourceChanged,
                          for_resources=("record",))
    config.add_subscriber(listener.on_server_flushed, ServerFlushed)
    config.add_subscriber(listener.on_collection_created, AfterResourceChanged,
                          for_resources=("collection",), for_actions=("create",))
    config.add_subscriber(listener.on_collection_updated, AfterResourceChanged,
                          for_resources=("collection",), for_actions=("update",))
    config.add_subscriber(listener.on_collection_deleted, AfterResourceChanged,
                          for_resources=("collection",), for_actions=("delete",))
    config.add_subscriber(listener.on_bucket_deleted, AfterResourceChanged,
                          for_resources=("bucket",), for_actions=("delete",))

    config.add_api_capability("elasticsearch",
                              description="Index and search records using ElasticSearch.",
                              url="https://github.com/Kinto/kinto-elasticsearch",
                              version=__version__)
