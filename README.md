![image](https://github.com/user-attachments/assets/b8c02a4a-0e16-49c4-8c12-c1934ef2e60e)

# Route Optimization API

This project provides a Django-based web API for determining the optimal refueling stops along a route between two addresses. It uses geospatial data, optimization techniques, and interactive maps to help users minimize travel costs and fuel consumption.

## Features

- Computes optimal refueling stops along a given route.
- Provides results as both JSON data and interactive HTML maps.
- Calculates total travel distance and associated fuel costs.
- Identifies states crossed during the journey.

## How It Works

### High-Level Workflow
1. **User Input:** The API receives a start and end address.
2. **Geocoding:** Converts addresses into geographical coordinates using Nominatim.
3. **Route Data:** Fetches route details (geometry and distance) using the OSRM API.
4. **State Traversal:** Identifies states crossed using GeoJSON state boundary data.
5. **Fuel Optimization:** Calculates optimal refueling stops based on factors like fuel prices, station proximity, and vehicle constraints.
6. **Visualization:** Outputs route data and refueling stops as JSON or an interactive HTML map.

### Core Components

#### API Endpoints
- `GET /optapi/<address1>/<address2>`
  - Returns route data and optimized refueling stops as JSON.
  - **Parameters:**
    - `address1` (str): Starting address.
    - `address2` (str): Ending address.
- `GET /optapi/map/<address1>/<address2>`
  - Returns an HTML map showing the route and refueling stops.
  - **Parameters:**
    - `address1` (str): Starting address.
    - `address2` (str): Ending address.

#### Utilities
- **Geocoding and Routing:**
  - `get_coordinates(address)`: Retrieves geographical coordinates for an address.
  - `get_route_data(start_address, end_address)`: Fetches route geometry and distance from OSRM.
- **Fuel Optimization:**
  - `refuel_optimizer(route_data, states_crossed)`: Computes optimal refueling plan based on route data and station details.
- **Map Visualization:**
  - `generate_map(route, markers)`: Creates an interactive map with the route and refueling stops.

## How to Use

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Django development server:
   ```bash
   python manage.py runserver
   ```
4. Access the API endpoints:
   - JSON response: `http://localhost:8000/optapi/<address1>/<address2>`
   - HTML map: `http://localhost:8000/optapi/map/<address1>/<address2>`

## Assumptions

- Vehicle parameters:
  - Maximum range: 500 miles per tank.
  - Fuel efficiency: 10 miles per gallon.
  - Refueling buffer: 75 miles of fuel reserve.
  - Maximum detour: 30 miles to a refueling station.
- GeoJSON state boundaries are used to identify states crossed.
- OSRM is assumed to be available for routing services.

## Benefits

- Provides cost-effective and efficient travel plans.
- Integrates interactive visualizations for better route understanding.
- Supports seamless geospatial data processing and optimization.

## Limitations

- Depends on external services (Nominatim, OSRM, GeoJSON).
- Limited to driving routes and fuel optimization scenarios.
- Requires preprocessed fuel station data with accurate pricing and locations.
- Does not account for real-time traffic or fuel price fluctuations.

## Dependencies

- Django: Web framework for API development.
- GeoPy: Geocoding library for address lookup.
- Numba: Accelerated numerical computations.
- NumPy, Pandas: Data manipulation and processing.
- SciPy: Optimization functions.
- Folium: Map visualization.
- Shapely, GeoPandas: Geospatial data handling.

## Contribution

Contributions are welcome! Please fork the repository, make changes, and submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Citation

Please if you find these useful in anyway, cite it or my github account, much appreciated!
