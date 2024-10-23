from flask import Flask, request
from google.auth import default as google_default_auth
from google.auth.transport.requests import Request as GoogleRequest
from firebase_admin import initialize_app
from functools import reduce
import os
import requests
import logging
import random
import json

initialize_app()
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Google Auth
creds, project = google_default_auth()
auth_req = GoogleRequest()

# Environment Variables
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")

# Constants
DEFAULT_PAGE_SIZE = 3
DEFAULT_NUM_RESULTS = 6
DEFAULT_ACTIVITY = "tourist attractions"


def get_request_params(param, default=None):
    print(f"Getting request params: {param}")
    request_json = request.get_json(silent=True)
    request_args = request.args
    print(f"request_json: {request_json}")
    print(f"request_args: {request_args}")

    # return (request_json or {}).get(param, default) or request_args.get(param, default)
    return (request_json or {}).get(param)

def get_address(region_code, locality, addressLines):

  payload = json.dumps({
    "address": {
      "regionCode": region_code,
      "locality": locality,
      "addressLines": [addressLines]
      }
    })
  try:
    validated_address = requests.post(
      f"https://addressvalidation.googleapis.com/v1:validateAddress",
      data=payload,
      headers={
        "Content-Type": "application/json"
        },
      params={
        "key": GOOGLE_PLACES_API_KEY
        }



    )
  except requests.RequestException as e:
    logging.error(f"Error fetching places: {e}")
    return []

  response_status = validated_address.status_code
  if response_status != 200:
    response = ""
  else:
    response = validated_address.json()

  return [{"response":response, "status":response_status}]


def get_places(city, activity, page_size=DEFAULT_PAGE_SIZE):
    text_query = f"{activity} in {city}"
    print(text_query)
    try:
        places_resp = requests.get(
            f"https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={
                "query": text_query,
                "key": GOOGLE_PLACES_API_KEY,
            },
        )
        places_resp.raise_for_status()

    except requests.RequestException as e:
        logging.error(f"Error fetching places: {e}")
        return []

    places = places_resp.json().get("results", [])
    places_info = [
        {
            "name": place.get("name"),
            "address": place.get("formatted_address"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "place_id": place.get("place_id"),
        }
        for place in places
    ][:page_size]

    #logging.info(f"Get places -- {text_query}, returning array of {len()}")

    return places_info


@app.route("/tourist_attractions", methods=["GET", "POST"])
def tourist_attractions():
    city = get_request_params("city")

    return {"results": get_places(city, DEFAULT_ACTIVITY)}


@app.route("/places_search", methods=["GET", "POST"])
def places_search():
    print(f"g")
    city = get_request_params("city")
    activity = get_request_params("activity")
    print(f"Getting resutls of {activity} in {city}")

    return {"results": get_places(city, activity)}

@app.route("/address_validation", methods=["POST"])
def address_validation():
    #city = get_request_params("city")
    #activity = get_request_params("activity")
    region_code = get_request_params("regionCode")
    locality = get_request_params("locality")
    addressLines = get_request_params("addressLines")

    return {"results": get_address(region_code, locality, addressLines)}


@app.route("/hotel_search", methods=["GET", "POST"])
def hotel_search():
    city = get_request_params("city")
    num_results = get_request_params("num_results", DEFAULT_NUM_RESULTS)

    return {"results": get_places(city, "hotels", page_size=num_results)}


@app.route("/places_search_tool", methods=["GET", "POST"])
def places_search_tool():
    """Args:
        city: name of the city
        place: name of the place (e.g. Hilton hotel)
        preferences: comma separated list of user preference
        pageSize: number of places to return

    Returns:
        Results with a list of activities
    """
    city = get_request_params("city")
    place = get_request_params("place")
    city_query = f"{place} {city}" if place and city else city
    print(f"city_query: {city_query}")
    activities_str = get_request_params("preferences", DEFAULT_ACTIVITY)
    activities = activities_str.split(",")
    page_size = get_request_params("page_size", DEFAULT_PAGE_SIZE)
    activity_page_size = round(page_size / len(activities)) + 1

    outputs = [
        get_places(city_query, activity, activity_page_size) for activity in activities
    ]
    output = reduce(lambda a, b: a + b, outputs)
    random.shuffle(output)
    return {"results": output[:page_size]}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
