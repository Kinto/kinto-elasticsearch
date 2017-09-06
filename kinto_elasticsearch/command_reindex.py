import sys

from pyramid.paster import bootstrap

from kinto.core.storage.exceptions import RecordNotFoundError
from kinto.core.storage import Sort


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    try:
        # XXX: use argsparse
        config_file, bucket_id, collection_id = args
    except ValueError:
        print("Usage: %s CONFIG BUCKET COLLECTION" % sys.argv[0])
        return 1

    print("Load config...")
    env = bootstrap(config_file)

    registry = env['registry']
    storage = registry.storage
    # XXX: exit cleanly if no indexer defined.
    indexer = registry.indexer

    # Open collection metadata.
    # XXX: https://github.com/Kinto/kinto/issues/710
    try:
        metadata = storage.get(parent_id="/buckets/%s" % bucket_id,
                               collection_id="collection",
                               object_id=collection_id)
    except RecordNotFoundError:
        print("No collection '%s' in bucket '%s'" % (collection_id, bucket_id))
        return 32

    schema = metadata.get("index:schema")
    # Give up if collection has no index mapping.
    if schema is None:
        print("No `index:schema` attribute found in collection metadata.")
        return 42

    # XXX: Are you sure?

    # Delete existing index.
    r = indexer.delete_index(bucket_id, collection_id)
    print("Old index deleted.")
    # Recreate the index with the new schema.
    indexer.create_index(bucket_id, collection_id, schema=schema)
    print("New index created.")

    # Fetch list of records and reindex.
    # XXX: we will reach the storage_fetch_limit, so we need pagination!
    pagination_rules = []
    while "not gone through all pages":
        records, count = storage.get_all(parent_id="/buckets/%s/collections/%s" % (bucket_id, collection_id),
                                         collection_id="record",
                                         pagination_rules=pagination_rules,
                                         sorting=[Sort('last_modified', -1)])

        if len(records) == 0:
            print("No records to index.")
            return 0
        try:
            with indexer.bulk() as bulk:
                for record in records:
                    bulk.index_record(bucket_id,
                                      collection_id,
                                      record=record,
                                      id_field="id")
                    print(".", end="")
        except elasticsearch.ElasticsearchException:
            logger.exception("Failed to index record")

        break # XXX pagination_rules = ...

    print("Done.")
    return 0
