from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils.maps import get_route_data, generate_map, get_states_crossed
from .utils.optimizer import refuel_optimizer


@api_view(["GET"])
def optimize_route_json(request, address1, address2):
    """
    Optimizes the route and returns the result as JSON.

    Args:
        request: The HTTP request object.
        address1 (str): The starting address.
        address2 (str): The ending address.

    Returns:
        Response: A JSON response containing the optimized route, distance, refuel stops, and total cost.
    """
    # Retrieve route data including coordinates and distance
    route_data = get_route_data(address1, address2)

    # Identify the states crossed by the route
    states_crossed = get_states_crossed(route_data["route"])

    # Optimize refueling stops and calculate the total cost
    stops = refuel_optimizer(route_data, states_crossed)

    # Build the response body with route data and optimization results
    response_body = {
        "route": route_data["route"],
        "distance": route_data["distance"],
        "stops": stops["refuel stops"],
        "cost": stops["total cost"],
    }

    # Return the response as JSON
    return Response(response_body)


@api_view(["GET"])
def optimize_route_html(request, address1, address2):
    """
    Optimizes the route and returns the result as an HTML map.

    Args:
        request: The HTTP request object.
        address1 (str): The starting address.
        address2 (str): The ending address.

    Returns:
        HttpResponse: An HTTP response containing an HTML representation of the route map with refuel stops.
    """
    # Retrieve route data including coordinates and distance
    route_data = get_route_data(address1, address2)

    # Identify the states crossed by the route
    states_crossed = get_states_crossed(route_data["route"])

    # Optimize refueling stops and calculate the total cost
    stops = refuel_optimizer(route_data, states_crossed)

    # Generate a map with the route and refuel stop markers
    geomap = generate_map(
        route_data["route"],
        markers=[eval(stop["coordinates"]) for stop in stops["refuel stops"]],
    )

    # Return the map as an HTML response
    return HttpResponse(geomap._repr_html_())
