from typing import List, Dict, Union
from scipy.optimize import minimize
from .maps import calculate_route_distance
from numba import njit
import numpy as np
import pandas as pd
import os

# Define problem parameters
CAR_RANGE = 500  # miles
FUEL_EFFICIENCY = 10  # miles / gallon
ALPHA = 75  # tank allowance before requiring refueling
MAXIMUM_DETOUR = 30  # assumption of total amount of detour distance to refuel


@njit
def find_closest_distance(route: np.ndarray, coord: np.ndarray) -> float:
    """
    Finds the closest distance between a given coordinate and a route.

    Args:
        route (np.ndarray): Array of [latitude, longitude] pairs representing the route.
        coord (np.ndarray): [latitude, longitude] coordinate to compare.

    Returns:
        float: The shortest distance in miles between the route and the coordinate.
    """
    # Calculate the distance from the given coordinate to each point in the route
    return min([calculate_route_distance(i, coord) for i in route])


@njit
def cost_function(
    gallons: np.ndarray,
    price_per_gallon: np.ndarray,
    detour_distances: np.ndarray,
) -> float:
    """
    Computes the total refueling cost, including fuel price and detour costs.

    Args:
        gallons (np.ndarray): Amount of fuel (in gallons) to purchase at each station.
        price_per_gallon (np.ndarray): Fuel price per gallon at each station.
        detour_distances (np.ndarray): Detour distances (in miles) to reach each station.

    Returns:
        float: Total cost of refueling along the route.
    """
    # Calculate total cost considering fuel price and detour fuel consumption
    return sum((gallons + 2 * detour_distances / FUEL_EFFICIENCY) * price_per_gallon)


@njit
def constraint(gallons: np.ndarray, distance: float) -> float:
    """
    Defines the inequality constraint for the optimization problem.

    Args:
        gallons (np.ndarray): Amount of fuel (in gallons) to purchase at each station.
        distance (float): Total route distance in miles.

    Returns:
        float: Remaining fuel after considering distance and constraints.
    """
    # Ensure total fuel purchased meets the route requirements with detours
    return (
        sum(gallons) - (distance + MAXIMUM_DETOUR - CAR_RANGE + ALPHA) / FUEL_EFFICIENCY
    )


def refuel_optimizer(
    route_data: dict,
    states_crossed: List[str],
    data_filename: str = "/statics/with_cords.csv",
) -> Dict:
    """
    Optimizes the refueling stops and costs along a route.

    Args:
        route_data (dict): Data containing route geometry and distance.
        states_crossed (List[str]): List of state codes the route crosses.
        data_filename (str, optional): Path to the CSV file with fuel station data. Default is "/statics/with_cords.csv".

    Returns:
        Dict: Refueling plan with stops, fuel purchased, and total cost.
    """
    # Load the fuel station data from the provided CSV file
    data = pd.read_csv(os.path.dirname(os.path.abspath(__file__)) + data_filename)

    # Filter stations within the states crossed and drop rows with missing data
    filtered_data = data[data["State"].isin(states_crossed)].dropna().drop_duplicates()

    # Calculate detour distances for each fuel station from the route
    detour_distances = (
        np.array(
            [
                find_closest_distance(
                    np.array([np.array(c) for c in route_data["route"]]),
                    np.array(eval(coord)),
                )
                for coord in filtered_data["Coordinates"]
            ]
        )
    ) * 100
    # Filter to find the nearest stations to the route
    filtered_data = filtered_data[detour_distances <= MAXIMUM_DETOUR]
    detour_distances = detour_distances[detour_distances <= MAXIMUM_DETOUR]

    # Determine the number of available fuel stations
    number_of_stations = len(filtered_data)

    # Extract fuel prices at each station
    price_per_gallon = np.array(filtered_data["Retail Price"])

    # Define bounds for fuel quantities at each station
    bounds = [(0, None)] * number_of_stations

    # Define constraints to ensure sufficient fuel for the route
    constraints = [
        {
            "type": "eq",
            "fun": constraint,
            "args": (route_data["distance"],),
        }
    ]

    # Initialize the fuel quantities evenly across stations
    initial_guess = [
        ((route_data["distance"] + ALPHA - CAR_RANGE) / FUEL_EFFICIENCY)
        / number_of_stations
    ] * number_of_stations
    # Perform the optimization to minimize total refueling cost
    refuel_result = minimize(
        cost_function,
        initial_guess,
        args=(price_per_gallon, detour_distances),
        constraints=constraints,
        bounds=bounds,
        tol=1e-3,
    )

    # Build the result for each fuel station
    result_per_station = [
        {
            "station": filtered_data["Truckstop Name"].tolist()[i],
            "fuel": refuel_result.x[i],
            "address": filtered_data["Address"].tolist()[i],
            "coordinates": filtered_data["Coordinates"].tolist()[i],
        }
        for i in range(len(refuel_result.x))
    ]

    # Calculate the total refueling cost
    total_refuel_cost = cost_function(
        np.round(refuel_result.x), price_per_gallon, detour_distances
    )

    # Filter out stations where no fuel was purchased
    result_per_station = filter(lambda m: m["fuel"] > 1, result_per_station)

    # Return the refueling stops and the total cost
    return {"refuel stops": result_per_station, "total cost": total_refuel_cost}
