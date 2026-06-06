"""Traffic simulator tool using networkx graph of London road network."""

import logging
import random

import networkx as nx

from config.settings import settings

logger = logging.getLogger(__name__)

# Sample London road network
_graph = None


def _build_network() -> nx.DiGraph:
    """Build a sample London road network graph."""
    G = nx.DiGraph()

    roads = [
        ("A1", "A10", 5), ("A10", "A406", 4), ("A406", "A1", 6),
        ("A2", "A20", 7), ("A20", "A2", 7), ("A2", "A206", 3),
        ("A3", "A24", 5), ("A24", "A3", 5), ("A3", "A316", 4),
        ("A4", "A40", 8), ("A40", "A406", 5), ("A4", "A316", 3),
        ("A5", "A41", 6), ("A41", "A406", 4), ("A5", "A406", 5),
        ("A406", "A10", 4), ("A406", "A1", 6), ("A406", "A5", 5),
        ("A406", "A41", 4), ("A406", "A40", 5),
        ("A205", "A2", 4), ("A205", "A3", 5), ("A205", "A24", 3),
        ("A316", "A4", 3), ("A316", "A3", 4),
        ("M25", "A1", 10), ("M25", "A2", 10), ("M25", "A3", 10),
        ("M25", "A4", 10), ("M25", "A5", 10),
        ("A13", "A406", 6), ("A13", "A2", 8),
    ]

    for src, dst, weight in roads:
        G.add_edge(src, dst, weight=weight, capacity=random.randint(1500, 3000))

    return G


def _get_graph() -> nx.DiGraph:
    global _graph
    if _graph is None:
        _graph = _build_network()
    return _graph


def _time_multiplier(time_of_day: str) -> float:
    """Return a congestion multiplier based on time of day."""
    try:
        hour = int(time_of_day.split(":")[0])
    except (ValueError, IndexError):
        hour = 12

    if 7 <= hour <= 9:
        return 1.8
    elif 16 <= hour <= 19:
        return 2.0
    elif 10 <= hour <= 15:
        return 1.2
    else:
        return 0.8


async def execute(road: str, duration_hours: float, time_of_day: str = "17:00") -> dict:
    """Simulate road closure impact on London traffic network."""
    try:
        G = _get_graph()
        road = road.upper()

        if road not in G.nodes:
            return {
                "affected_roads": [],
                "avg_delay_minutes": 0,
                "total_rerouted": 0,
                "recommendation": f"Road '{road}' not found in network model.",
            }

        multiplier = _time_multiplier(time_of_day)

        # Find affected roads (neighbors)
        predecessors = list(G.predecessors(road))
        successors = list(G.successors(road))
        affected = list(set(predecessors + successors))

        # Simulate rerouting
        G_closed = G.copy()
        G_closed.remove_node(road)

        rerouted_count = 0
        total_delay = 0.0

        for pred in predecessors:
            for succ in successors:
                try:
                    original_path = nx.shortest_path_length(G, pred, succ, weight="weight")
                    new_path = nx.shortest_path_length(G_closed, pred, succ, weight="weight")
                    delay = (new_path - original_path) * multiplier * duration_hours
                    total_delay += delay
                    rerouted_count += random.randint(200, 800)
                except nx.NetworkXNoPath:
                    total_delay += 15 * multiplier
                    rerouted_count += random.randint(500, 1500)

        avg_delay = total_delay / max(len(predecessors) * len(successors), 1)

        # Generate recommendation
        if avg_delay > 20:
            recommendation = f"Critical impact. Recommend diverting traffic via {affected[0] if affected else 'alternative routes'} and deploying traffic officers."
        elif avg_delay > 10:
            recommendation = f"Moderate impact. Suggest updating signage to route via {', '.join(affected[:2])}."
        else:
            recommendation = "Low impact. Standard traffic management should suffice."

        return {
            "affected_roads": affected,
            "avg_delay_minutes": round(avg_delay, 1),
            "total_rerouted": rerouted_count,
            "recommendation": recommendation,
        }

    except Exception as e:
        logger.exception("Simulator failed")
        return {
            "affected_roads": [],
            "avg_delay_minutes": 0,
            "total_rerouted": 0,
            "recommendation": f"Simulation error: {str(e)}",
        }
