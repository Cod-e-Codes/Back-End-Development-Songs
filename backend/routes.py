from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)


def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################


@app.route("/count")
def count():
    """return length of data"""
    count = db.songs.count_documents({})
    return {"count": count}, 200


@app.route("/song")
def songs():
    """Return all songs in the database"""
    # Find all documents in the songs collection
    songs_cursor = db.songs.find({})

    # Convert the cursor to a list and parse the JSON
    # to handle MongoDB-specific types like ObjectId
    songs_list = parse_json(list(songs_cursor))

    # Return the songs as a dictionary with "songs" key
    # and HTTP 200 OK status code
    return {"songs": songs_list}, 200


@app.route("/song/<int:id>")
def get_song_by_id(id):
    """Retrieve a specific song by its ID"""
    # Convert id to integer to match the database schema
    # Use find_one to get the first matching document
    song = db.songs.find_one({"id": id})

    # Check if song is found
    if song is None:
        # Return 404 Not Found with message if song doesn't exist
        return {"message": "song with id not found"}, 404

    # Parse the song document and return with 200 OK status
    return parse_json(song), 200


@app.route("/song", methods=["POST"])
def create_song():
    """Create a new song in the database"""
    # Get the song data from the request body
    song = request.get_json()

    # Check if a song with the same id already exists
    existing_song = db.songs.find_one({"id": song.get('id')})

    # If song already exists, return 302 Found status
    if existing_song is not None:
        return {"Message": f"song with id {song['id']} already present"}, 302

    # Insert the new song into the database
    # Note: We're using insert_one which returns an InsertOneResult object
    result = db.songs.insert_one(song)

    # Return the inserted document's ID with 201 Created status
    return {"inserted id": parse_json(result.inserted_id)}, 201


@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Update an existing song in the database"""
    # Get the song data from the request body
    update_data = request.get_json()

    # Check if the song exists
    existing_song = db.songs.find_one({"id": id})

    # If song does not exist, return 404 Not Found
    if existing_song is None:
        return {"message": "song not found"}, 404

    # Perform the update
    # Use $set to update only the provided fields
    update_result = db.songs.update_one(
        {"id": id},
        {"$set": update_data}
    )

    # Check if anything was actually modified
    if update_result.modified_count == 0:
        return {"message": "song found, but nothing updated"}, 200

    # Retrieve the updated song
    updated_song = db.songs.find_one({"id": id})

    # Return the updated song with 201 Created status
    return parse_json(updated_song), 201


@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete a song from the database"""
    # Attempt to delete the song with the specified id
    delete_result = db.songs.delete_one({"id": id})

    # Check if any document was deleted
    if delete_result.deleted_count == 0:
        # If no song was found and deleted, return 404 Not Found
        return {"message": "song not found"}, 404

    # If song was successfully deleted, return 204 No Content
    # This means the request was successful but there's no content to return
    return '', 204
