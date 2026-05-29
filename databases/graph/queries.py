"""
TransitFlow — Neo4j Graph Database Layer
=========================================
This module handles all queries to Neo4j.

GRAPH ROLE:
  - Model the dual transit network (city metro M1–M4 + national rail NR1–NR2)
  - Find fastest routes (Dijkstra by travel_time_min via APOC)
  - Find cheapest routes (Dijkstra by fare via APOC)
  - Find alternative routes avoiding a given station
  - Find cross-network interchange paths (metro → rail or rail → metro)
  - Show delay ripple: which stations are affected within N hops

STUDENT TASK
------------
Design your graph schema (node labels, relationship types, properties)
based on the data in train-mock-data/, seed it with skeleton/seed_neo4j.py,
then implement the query_ functions below.

Functions prefixed with `query_` are called by the agent (skeleton/agent.py).
"""

from __future__ import annotations

from neo4j import GraphDatabase  # pyrefly: ignore [missing-import]

from skeleton.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def _driver():
    """Return a Neo4j driver. Caller is responsible for closing."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# ── Example ───────────────────────────────────────────────────────────────────
# The block below shows the query pattern: open a session, run Cypher, return data.

def example_count_nodes() -> int:
    """Example: count all nodes currently in the graph."""
    with _driver() as driver:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS total")
            return result.single()["total"]


def _network_relationship_types(network: str, origin_id: str = "", destination_id: str = "") -> list[str]:
    """Return relationship types allowed for a network selector."""
    network = (network or "auto").lower()
    if network == "metro":
        return ["METRO_LINK"]
    if network == "rail":
        return ["RAIL_LINK"]
    if origin_id.upper().startswith("MS") and destination_id.upper().startswith("MS"):
        return ["METRO_LINK"]
    if origin_id.upper().startswith("NR") and destination_id.upper().startswith("NR"):
        return ["RAIL_LINK"]
    return ["METRO_LINK", "RAIL_LINK", "INTERCHANGE_TO"]


def _station_to_dict(station) -> dict:
    """Convert a Neo4j node to a plain dict."""
    data = dict(station)
    data["labels"] = sorted(list(station.labels))
    return data


def _relationship_type(relationship) -> str:
    """Return the relationship type as a string."""
    return getattr(relationship, "type", type(relationship).__name__)


def _build_legs(stations: list[dict], relationships) -> list[dict]:
    """Convert a Neo4j path into serialisable leg dictionaries."""
    legs = []
    for index, rel in enumerate(relationships):
        start = stations[index]
        end = stations[index + 1]
        legs.append(
            {
                "from_station_id": start["station_id"],
                "from_name": start["name"],
                "to_station_id": end["station_id"],
                "to_name": end["name"],
                "relationship_type": _relationship_type(rel),
                "line": rel.get("line"),
                "travel_time_min": rel.get("travel_time_min", 0),
                "distance": rel.get("distance"),
                "standard_fare_usd": float(rel.get("standard_fare_usd", 0) or 0),
                "first_fare_usd": float(rel.get("first_fare_usd", 0) or 0),
            }
        )
    return legs


def _empty_route(origin_id: str, destination_id: str) -> dict:
    """Return the standard empty route payload."""
    return {
        "found": False,
        "origin_id": origin_id,
        "destination_id": destination_id,
        "total_time_min": None,
        "path": [],
        "legs": [],
    }


def _path_query(weight_expression: str) -> str:
    """Build the shared weighted path query."""
    return f"""
        MATCH (origin:Station {{station_id: $origin_id}})
        MATCH (destination:Station {{station_id: $destination_id}})
        MATCH path = (origin)-[rels:METRO_LINK|RAIL_LINK|INTERCHANGE_TO*0..20]-(destination)
        WHERE all(rel IN rels WHERE type(rel) IN $relationship_types)
          AND all(station IN nodes(path) WHERE coalesce(station.is_closed, false) = false)
          AND all(
              index IN range(0, size(nodes(path)) - 1)
              WHERE single(station IN nodes(path) WHERE elementId(station) = elementId(nodes(path)[index]))
          )
        WITH path, rels, {weight_expression} AS total_weight
        ORDER BY total_weight ASC, length(path) ASC
        LIMIT 1
        RETURN nodes(path) AS stations,
               rels AS relationships,
               total_weight
    """

# ─────────────────────────────────────────────────────────────────────────────


# ── FASTEST ROUTE (Dijkstra by travel_time_min) ───────────────────────────────

def query_shortest_route(
    origin_id: str,
    destination_id: str,
    network: str = "auto",
) -> dict:
    """
    Find the fastest path between two stations, minimising total travel time.
    Uses weighted Cypher path search over the seeded transit graph.

    Args:
        origin_id:       e.g. "MS01" or "NR01"
        destination_id:  e.g. "MS09" or "NR05"
        network:         "metro", "rail", or "auto" (inferred from IDs)

    Returns:
        dict with keys: found, origin_id, destination_id,
                        total_time_min, path (list of station dicts), legs
    """
    relationship_types = _network_relationship_types(network, origin_id, destination_id)
    query = _path_query(
        "reduce(total = 0.0, rel IN rels | total + coalesce(rel.travel_time_min, 0))"
    )

    with _driver() as driver:
        with driver.session() as session:
            record = session.run(
                query,
                origin_id=origin_id,
                destination_id=destination_id,
                relationship_types=relationship_types,
            ).single()

    if not record:
        return _empty_route(origin_id, destination_id)

    stations = [_station_to_dict(station) for station in record["stations"]]
    legs = _build_legs(stations, record["relationships"])
    return {
        "found": True,
        "origin_id": origin_id,
        "destination_id": destination_id,
        "total_time_min": record["total_weight"],
        "path": stations,
        "legs": legs,
    }


# ── CHEAPEST ROUTE (Dijkstra by fare) ────────────────────────────────────────

def query_cheapest_route(
    origin_id: str,
    destination_id: str,
    network: str = "auto",
    fare_class: str = "standard",
) -> dict:
    """
    Find the cheapest path between two stations, minimising total estimated fare.

    Args:
        origin_id:       e.g. "NR01"
        destination_id:  e.g. "NR05"
        network:         "metro", "rail", or "auto"
        fare_class:      "standard" or "first" (national rail only)

    Returns:
        dict with found, total_fare_usd (approximate), stations, legs
    """
    relationship_types = _network_relationship_types(network, origin_id, destination_id)
    fare_class = (fare_class or "standard").lower()
    query = _path_query(
        """
        reduce(
            total = 0.0,
            rel IN rels |
            total + coalesce(
                CASE $fare_class
                    WHEN "first" THEN rel.first_fare_usd
                    ELSE rel.standard_fare_usd
                END,
                0
            )
        )
        """
    )

    with _driver() as driver:
        with driver.session() as session:
            record = session.run(
                query,
                origin_id=origin_id,
                destination_id=destination_id,
                relationship_types=relationship_types,
                fare_class=fare_class,
            ).single()

    if not record:
        return {
            "found": False,
            "origin_id": origin_id,
            "destination_id": destination_id,
            "fare_class": fare_class,
            "total_fare_usd": None,
            "stations": [],
            "legs": [],
        }

    stations = [_station_to_dict(station) for station in record["stations"]]
    return {
        "found": True,
        "origin_id": origin_id,
        "destination_id": destination_id,
        "fare_class": fare_class,
        "total_fare_usd": round(float(record["total_weight"]), 2),
        "stations": stations,
        "legs": _build_legs(stations, record["relationships"]),
    }


# ── ALTERNATIVE ROUTES (avoiding a station) ───────────────────────────────────

def query_alternative_routes(
    origin_id: str,
    destination_id: str,
    avoid_station_id: str,
    network: str = "auto",
    max_routes: int = 3,
) -> list[list[dict]]:
    """
    Find paths between two stations that avoid a specific intermediate station.
    Useful for routing around a delayed or closed station.

    Args:
        origin_id:         e.g. "NR01"
        destination_id:    e.g. "NR05"
        avoid_station_id:  e.g. "NR03"
        network:           "metro", "rail", or "auto"
        max_routes:        max number of alternatives to return

    Returns:
        List of routes, each route is a list of leg dicts
    """
    relationship_types = _network_relationship_types(network, origin_id, destination_id)
    max_routes = max(1, min(int(max_routes), 10))

    query = """
        MATCH (origin:Station {station_id: $origin_id})
        MATCH (destination:Station {station_id: $destination_id})
        MATCH path = (origin)-[rels:METRO_LINK|RAIL_LINK|INTERCHANGE_TO*1..20]-(destination)
        WHERE all(rel IN rels WHERE type(rel) IN $relationship_types)
          AND all(station IN nodes(path) WHERE coalesce(station.is_closed, false) = false)
          AND all(
              index IN range(0, size(nodes(path)) - 1)
              WHERE single(station IN nodes(path) WHERE elementId(station) = elementId(nodes(path)[index]))
          )
          AND all(
              station IN nodes(path)
              WHERE station.station_id <> $avoid_station_id
                 OR station.station_id IN [$origin_id, $destination_id]
          )
        WITH path, rels,
             reduce(total = 0.0, rel IN rels | total + coalesce(rel.travel_time_min, 0)) AS total_time_min
        ORDER BY total_time_min ASC, length(path) ASC
        LIMIT $max_routes
        RETURN nodes(path) AS stations,
               rels AS relationships
    """

    with _driver() as driver:
        with driver.session() as session:
            records = list(
                session.run(
                    query,
                    origin_id=origin_id,
                    destination_id=destination_id,
                    avoid_station_id=avoid_station_id,
                    relationship_types=relationship_types,
                    max_routes=max_routes,
                )
            )

    routes = []
    for record in records:
        stations = [_station_to_dict(station) for station in record["stations"]]
        routes.append(_build_legs(stations, record["relationships"]))
    return routes


# ── CROSS-NETWORK INTERCHANGE PATH ───────────────────────────────────────────

def query_interchange_path(origin_id: str, destination_id: str) -> dict:
    """
    Find a path between a metro station and a national rail station (or vice versa)
    crossing the network boundary via interchange relationships.

    Args:
        origin_id:       e.g. "MS03" (metro) or "NR05" (national rail)
        destination_id:  e.g. "NR05" (national rail) or "MS09" (metro)

    Returns:
        dict with found, stations list, interchange points, total_time_min
    """
    route = query_shortest_route(origin_id, destination_id, network="auto")
    if not route["found"]:
        return {
            "found": False,
            "origin_id": origin_id,
            "destination_id": destination_id,
            "stations": [],
            "interchange_points": [],
            "total_time_min": None,
            "legs": [],
        }

    interchange_points = []
    for leg in route["legs"]:
        if leg["relationship_type"] != "INTERCHANGE_TO":
            continue
        interchange_points.extend(
            [
                {"station_id": leg["from_station_id"], "name": leg["from_name"]},
                {"station_id": leg["to_station_id"], "name": leg["to_name"]},
            ]
        )

    seen = set()
    unique_interchanges = []
    for point in interchange_points:
        if point["station_id"] in seen:
            continue
        seen.add(point["station_id"])
        unique_interchanges.append(point)

    return {
        "found": True,
        "origin_id": origin_id,
        "destination_id": destination_id,
        "stations": route["path"],
        "interchange_points": unique_interchanges,
        "total_time_min": route["total_time_min"],
        "legs": route["legs"],
    }


# ── DELAY RIPPLE ANALYSIS ─────────────────────────────────────────────────────

def query_delay_ripple(delayed_station_id: str, hops: int = 2) -> list[dict]:
    """
    Find all stations within N hops of a delayed or disrupted station.
    Works on both metro and national rail networks.

    Args:
        delayed_station_id: e.g. "NR03" or "MS01"
        hops:               how many connections out to search (default 2)

    Returns:
        List of dicts: {station_id, name, hops_away, lines_affected}
    """
    max_hops = max(1, min(int(hops), 6))
    query = f"""
        MATCH (delayed:Station {{station_id: $delayed_station_id}})
        MATCH path = (delayed)-[rels:METRO_LINK|RAIL_LINK|INTERCHANGE_TO*1..{max_hops}]-(station:Station)
        WHERE station.station_id <> $delayed_station_id
          AND coalesce(station.is_closed, false) = false
        RETURN station AS station,
               min(length(path)) AS hops_away,
               collect([rel IN rels WHERE rel.line IS NOT NULL | rel.line]) AS line_groups
        ORDER BY hops_away ASC, station.station_id ASC
    """

    with _driver() as driver:
        with driver.session() as session:
            records = list(session.run(query, delayed_station_id=delayed_station_id))

    ripples = []
    for record in records:
        station = record["station"]
        lines = sorted(
            {
                line
                for group in record["line_groups"]
                for line in group
                if line and line != "interchange"
            }
        )
        ripples.append(
            {
                "station_id": station["station_id"],
                "name": station["name"],
                "hops_away": record["hops_away"],
                "lines_affected": lines,
            }
        )
    return ripples


# ── STATION CONNECTIONS ───────────────────────────────────────────────────────

def query_station_connections(station_id: str) -> list[dict]:
    """
    List all direct connections from a given station.

    Args:
        station_id: e.g. "MS01" or "NR01"

    Returns:
        List of dicts describing each directly connected station and link.
    """
    query = """
        MATCH (station:Station {station_id: $station_id})
        MATCH (station)-[rel:METRO_LINK|RAIL_LINK|INTERCHANGE_TO]-(connected:Station)
        WHERE coalesce(connected.is_closed, false) = false
        RETURN DISTINCT connected AS connected,
               type(rel) AS relationship_type,
               rel.line AS line,
               rel.travel_time_min AS travel_time_min,
               rel.distance AS distance,
               rel.standard_fare_usd AS standard_fare_usd,
               rel.first_fare_usd AS first_fare_usd
        ORDER BY relationship_type, line, connected.station_id
    """

    with _driver() as driver:
        with driver.session() as session:
            records = list(session.run(query, station_id=station_id))

    return [
        {
            "station_id": record["connected"]["station_id"],
            "name": record["connected"]["name"],
            "relationship_type": record["relationship_type"],
            "line": record["line"],
            "travel_time_min": record["travel_time_min"],
            "distance": record["distance"],
            "standard_fare_usd": float(record["standard_fare_usd"] or 0),
            "first_fare_usd": float(record["first_fare_usd"] or 0),
        }
        for record in records
    ]
