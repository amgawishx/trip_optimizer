import logging
from typing import List, Dict, Union
from geopy.geocoders import Nominatim
from shapely.geometry import shape, box, Point
from numba import njit
from requests import get
from json import load
import geopandas as gpd
import numpy as np
import folium
import os

METER_TO_MILE_FACTOR = 0.000621371

# Configure logging with different levels
logging.basicConfig(level=logging.INFO)


def get_coordinates(address: str) -> List[float]:
    """
    Retrieves the geographical coordinates (latitude and longitude) for a given address.

    Args:
        address (str): The address to geocode.

    INFO: Logs when this function is called.
    """
    logger = logging.getLogger(__name__)

    # Initialize the geocoder
    logger.debug("Initializing geocoder")
    geolocator = Nominatim(user_agent="geodecode", timeout=10)

    # Geocode the address and return the coordinates
    try:
        location = geolocator.geocode(address)
        logger.info(f"Geocoded successfully: {location}")
        return [location.longitude, location.latitude]
    except Exception as e:
        logger.error(f"Error geocoding {address}: {str(e)}")


def get_route_data(
    start_address: str, end_address: str
) -> Dict[str, Union[List[List[float]], float]]:
    """
    Retrieves route data between two addresses.

    Args:
        start_address (str): The starting address for the route.
        end_address (str): The ending address for the route.

    WARNING: Could not find routes due to API error - check if endpoints are correct and permissions.
    INFO: Successfully retrieved route data with distance in miles.
    """
    logger = logging.getLogger(__name__)

    try:
        # Build the query URL for the OSRM API
        query = f"{osrm_url}/{start_coord};{end_coord}?overview=full&geometries=geojson"

        # Send the request to the OSRM API
        response = get(query).json()

        if "error" in response:
            logger.error(f"API Error: {response['error']}")
            raise Exception("OSRM API returned error")

        route_data = {
            "route": route_geometry,
            "distance": response["routes"][0]["distance"] * METER_TO_MILE_FACTOR,
        }

        return route_data
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Request failed for addresses {start_address}-{end_address}: {str(e)}"
        )
        raise


@njit
def calculate_route_distance(coord1: np.ndarray, coord2: np.ndarray) -> float:
    """
    Calculate the taxicab (Manhattan) distance in miles between two geographical coordinates.

    INFO: Performs calculations based on latitude and longitude.
    """
    logger = logging.getLogger(__name__)

    try:
        # Constants for conversion
        lat_miles = 69.0  # 1 degree of latitude is approximately 69 miles
        avg_latitude = (coord1[0] + coord2[0]) / 2

        lon_miles = 69.0 * np.cos(
            np.radians(avg_latitude)
        )  # Adjust longitude to miles based on latitude

        distance = lat_miles * abs(coord1[0] - coord2[0]) + lon_miles * abs(
            coord1[1] - coord2[1]
        )
        logger.debug(f"Calculated distance: {distance} miles")

        return abs(distance)
    except Exception as e:
        logger.error(
            f"Error in calculate_route_distance for coordinates {coord1}-{coord2}: {str(e)}"
        )
        raise


def generate_map(
    route: List[List[float]],
    markers: List[List[float]] = None,
    save_name: str = "/statics/route_map.html",
) -> folium.Map:
    """
    Generates a folium map with a route and optional markers.

    INFO: Initializes the map centered on the starting point.
    WARNING: Map generation failed to load due to marker data issues
    """
    logger = logging.getLogger(__name__)

    try:
        # Reverse coordinates for Folium compatibility
        reversed_route = [[lat, lon] for [lon, lat] in route]

        if markers is not None:
            reversed_markers = [marker[::-1] for marker in markers]

        map_route = folium.Map(location=reversed_route[0])
        return map_route  # This will raise an exception if called without a valid route
    except Exception as e:
        logger.error(f"Error generating map: {str(e)}")
        raise


def simplify_state_geometries(states_geojson: str, tolerance: float) -> Dict:
    """
    Simplifies state geometries and returns the simplified GeoJSON data.

    Args:
        states_geojson (str): Path to the GeoJSON file containing state boundaries.
        tolerance (float): Tolerance for simplification (higher means more simplified).

    Returns:
        Dict: Simplified GeoJSON data.
    """
    # Read the GeoJSON file into a GeoDataFrame
    states = gpd.read_file(states_geojson)

    # Simplify the geometries of the states using the specified tolerance
    states["geometry"] = states["geometry"].simplify(tolerance, preserve_topology=True)

    # Return the simplified GeoJSON data
    return states


def build_spatial_index(states_geojson: str) -> Dict:
    """
    Builds a spatial index for states using their bounding boxes and simplified geometries.

    Args:
        states_geojson (str): Path to the GeoJSON file containing state boundaries.

    Returns:
        Dict: Spatial index with state names, bounding boxes, and simplified geometries.
    """
    # Simplify the state geometries for better performance
    simplified_geojson = simplify_state_geometries(states_geojson, tolerance=0.1)

    # Initialize an empty dictionary to hold the spatial index
    spatial_index = {}

    # Iterate through each state's geometry
    for _, row in simplified_geojson.iterrows():
        state_name = row["abbr"]  # Extract the state's abbreviation
        geometry = row["geometry"]  # Extract the state's geometry
        bounding_box = geometry.bounds  # Calculate the bounding box for the geometry

        # Add the state's data to the spatial index
        spatial_index[state_name] = {
            "geometry": geometry,
            "bounding_box": box(*bounding_box),
        }

    # Return the constructed spatial index
    return spatial_index


def get_states_crossed(
    coordinates: List[List[float]], geojson_path="/statics/us_states.geojson"
) -> List[str]:
    """
    Get the state codes crossed by a route.

    Args:
        coordinates (List[List[float]]): List of [latitude, longitude] pairs for the route.
        geojson_path (str, optional): Path to the GeoJSON file containing state boundaries. Default is "/statics/us_states.geojson".

    Returns:
        List[str]: A list of state codes crossed by the route.
    """
    # Initialize a list to store traversed states
    traversed_states = []

    # Build the spatial index using the provided GeoJSON file
    spatial_index = build_spatial_index(
        os.path.dirname(os.path.abspath(__file__)) + geojson_path
    )

    # Keep track of the current state
    current_state = None

    # Iterate through each point in the route
    for point in coordinates:
        point_geom = Point(point)  # Create a Point geometry for the current coordinate
        state_found = None  # Reset the state found

        # Check if the point lies in the bounding box of the current state
        if current_state and spatial_index[current_state]["bounding_box"].contains(
            point_geom
        ):
            # If so, check if it lies within the geometry of the current state
            if spatial_index[current_state]["geometry"].contains(point_geom):
                state_found = current_state

        # If the point is not in the current state, search all states
        if not state_found:
            for state_code, data in spatial_index.items():
                # Check if the point lies within the bounding box and geometry
                if data["bounding_box"].contains(point_geom) and data[
                    "geometry"
                ].contains(point_geom):
                    state_found = state_code
                    break

        # Add the state to the list if it has changed
        if state_found and state_found != current_state:
            traversed_states.append(state_found)
            current_state = state_found

    # Return the list of traversed states
    return traversed_states
