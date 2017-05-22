import pkg_resources

from kinto.core import load_default_settings
from kinto.core.events import ResourceChanged

from . import indexer
from . import listener


#: Module version, as defined in PEP-0396.
__version__ = pkg_resources.get_distribution(__package__).version


DEFAULT_SETTINGS = {
    'elasticsearch.refresh_enabled': False
}


def includeme(config):
    # Load settings from environment and apply defaults.
    load_default_settings(config, DEFAULT_SETTINGS)

    # Register a global indexer object
    config.registry.indexer = indexer.load_from_config(config)

    # Activate end-points.
    config.scan("kinto_elasticsearch.views")

    config.add_subscriber(listener.on_record_changed, ResourceChanged,
                          for_resources=("record",))

    config.add_api_capability("elasticsearch",
                              description="Index and search records using ElasticSearch.",
                              url="https://github.com/Kinto/kinto-elasticsearch",
                              version=__version__)
