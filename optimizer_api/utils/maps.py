from typing import List, Dict, Union
from geopy.geocoders import Nominatim
from geopy.exc import GeopyError
from shapely.geometry import shape, box, Point
from numba import njit
from requests import get
from json import load
import geopandas as gpd
import numpy as np
import folium
import os


METER_TO_MILE_FACTOR = 0.000621371


def get_coordinates(address: str) -> List[float]:
    """
    Retrieves the geographical coordinates (latitude and longitude) for a given address.

    Args:
        address (str): The address to geocode.

    Returns:
        List[float]: A list containing the latitude and longitude of the address.
    """
    # Initialize the geocoder
    geolocator = Nominatim(user_agent="geodecode", timeout=10)

    # Geocode the address and return the coordinates
    location = geolocator.geocode(address)
    return [location.longitude, location.latitude]


def get_route_data(
    start_address: str, end_address: str
) -> Dict[str, Union[List[List[float]], float]]:
    """
    Retrieves route data, including coordinates and distance, between two addresses.

    Args:
        start_address (str): The starting address for the route.
        end_address (str): The ending address for the route.

    Returns:
        Dict[str, Union[List[List[float]], float]]: A dictionary with the route coordinates
        and the total distance in meters.
    """
    osrm_url = "http://router.project-osrm.org/route/v1/driving/"

    # Get coordinates for the start and end addresses
    start_coord = "{},{}".format(*get_coordinates(start_address))
    end_coord = "{},{}".format(*get_coordinates(end_address))

    # Build the query URL for the OSRM API
    query = f"{osrm_url}/{start_coord};{end_coord}?overview=full&geometries=geojson"

    # Send the request to the OSRM API
    response = get(query).json()

    # Extract route geometry and distance from the response
    route_geometry = response["routes"][0]["geometry"]["coordinates"]

    # Return the route coordinates and total distance in miles
    return {
        "route": route_geometry,
        "distance": response["routes"][0]["distance"] * METER_TO_MILE_FACTOR,
    }


@njit
def calculate_route_distance(coord1: np.ndarray, coord2: np.ndarray) -> float:
    """
    Calculate the taxicab (Manhattan) distance in miles between two geographical coordinates.

    Args:
        coord1 (np.ndarray): [latitude, longitude] of the first point.
        coord2 (np.ndarray): [latitude, longitude] of the second point.

    Returns:
        float: Distance in miles.
    """
    # Constants for conversion
    lat_miles = 69.0  # 1 degree of latitude is approximately 69 miles
    avg_latitude = (coord1[0] + coord2[0]) / 2
    lon_miles = 69.0 * np.cos(
        np.radians(avg_latitude)
    )  # Adjust longitude to miles based on latitude

    # Calculate the Manhattan distance
    distance = lat_miles * abs(coord1[0] - coord2[0]) + lon_miles * abs(
        coord1[1] - coord2[1]
    )
    return abs(distance)


def generate_map(
    route: List[List[float]],
    markers: List[List[float]] = None,
    save_name: str = "/statics/route_map.html",
) -> folium.Map:
    """
    Generates a folium map with a route and optional markers.

    Args:
        route (List[List[float]]): List of [latitude, longitude] pairs for the route.
        markers (List[List[float]], optional): Additional marker coordinates. Default is None.
        save_name (str, optional): File name to save the map as an HTML file. Default is "route_map.html".

    Returns:
        folium.Map: The generated map object.
    """
    # Reverse coordinates from [lon, lat] to [lat, lon] for Folium compatibility
    route = [[lat, lon] for lon, lat in route]

    # Initialize the map centered at the first point of the route
    map_route = folium.Map(location=route[0])

    # Add a polyline for the route
    folium.PolyLine(locations=route, color="blue", weight=5, opacity=0.8).add_to(
        map_route
    )

    # Add markers for the start and end points of the route
    folium.Marker(location=route[0], tooltip="Start").add_to(map_route)
    folium.Marker(location=route[-1], tooltip="End").add_to(map_route)

    # Add additional markers if provided
    if markers:
        for index, marker in enumerate(markers):
            folium.Marker(location=marker[::-1], tooltip=f"Stop #{index + 1}").add_to(
                map_route
            )

    # Fit and save the map to an HTML file
    map_route.fit_bounds([route[0], route[-1]])
    map_route.save(os.path.dirname(os.path.abspath(__file__)) + save_name)

    # Return the map object
    return map_route


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
