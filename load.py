"""
Load OpenStreetMap data on Kinto, and take advantage of a ElasticSearch geo-index.
"""
import requests
import kinto_http


server = "http://localhost:8888/v1"
bucket = "restaurants"
collection = "pizzerias"
auth = ("user", "pass")

# Create the destination bucket and collection.
client = kinto_http.Client(server_url=server, auth=auth)
client.create_bucket(id=bucket, if_not_exists=True)
# Define the ElasticSearch mapping in the collection metadata.
collection_metadata = {
    "index:schema": {
        "properties": {
            "name": {
                "type": "text"
            },
            "location": {
                "type": "geo_point"
            }
        }
    }
}
# Let anonymous users read the records (online map demo).
collection_permissions = {
    "read": ["system.Everyone"]
}
client.create_collection(id=collection, bucket=bucket, data=collection_metadata,
                         permissions=collection_permissions, if_not_exists=True)

# Fetch OpenStreetMap data.
# This is a GeoJSON export of the following query on from http://overpass-turbo.eu
# area[name="Italia"];(node["cuisine"="pizza"](area););out;
pizzerias_export = "https://gist.githubusercontent.com/leplatrem/887e61efc1a7dfc7a68bcdf170d1ced9/raw/c0507d874ebe84923d51b2db7990af465eb9cf66/export.geoson"
export = requests.get(pizzerias_export).json()

# Create Kinto records for each geometry.
with client.batch() as batch:
    for pizzeria in export["features"]:
        record = {
            "id": pizzeria["id"].replace("node/", ""),
            "name": pizzeria["properties"].get("name"),
            "location": pizzeria["geometry"]["coordinates"],
        }
        batch.create_record(data=record, bucket=bucket, collection=collection)
