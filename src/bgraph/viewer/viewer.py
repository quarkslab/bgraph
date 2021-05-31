import logging
import functools

import networkx as nx  # type: ignore

import bgraph
from bgraph.types import List, Union, Dict, Set, NodeType, Tuple, Optional, overload
import bgraph.exc


logger: logging.Logger = bgraph.utils.create_logger(__name__)
"""Logger."""


DEFAULT_TYPES: List[NodeType] = [
    "cc_library_shared",
    "cc_library",
    "cc_binary",
    "cc_library_static",
    "android_app",
]
"""Default soong types to consider"""


@overload
def get_node_type(node_d: Dict) -> NodeType:
    ...


@overload
def get_node_type(node_d: Dict, all_types: bool) -> List[NodeType]:
    ...


def get_node_type(
    node_d: Dict, all_types: bool = False
) -> Union[NodeType, List[NodeType]]:
    """Get the node type

    Sources nodes (e.g leaves) have no data associated so we use this fact.

    :param node_d A node
    :param all_types Optional. Return all the types possible for the node
    :return Type(s) of the node
    """
    try:
        node_types = [
            node[bgraph.parsers.SoongParser.SECTION_TYPE] for node in node_d["data"]
        ]
    except (TypeError, KeyError):
        return "source" if all_types is False else ["source"]

    if all_types:
        return node_types
    else:
        # Return only the first node type
        return node_types.pop()


def match_node(graph_srcs: List[str], node_name: str) -> str:
    """Search for a node matching the name given as an argument.

    :param graph_srcs: A list of source node in the graph
    :param node_name: A node name
    :return: A node
    """

    potential_results = [node for node in graph_srcs if node_name in node]

    if not potential_results:
        raise bgraph.exc.BGraphNodeNotFound("Found 0 results")

    elif len(potential_results) > 1:
        # TODO(dm) : We have a problem here because we have too many nodes that may
        #  match but it is not supposed to happen.
        raise bgraph.exc.BGraphTooManyNodes("Found many results - refine the search")

    return potential_results.pop()


@functools.lru_cache(maxsize=8)
def get_graph_srcs(graph: nx.DiGraph) -> List[str]:
    """Filter the graph to return only source nodes.

    This method is used to improve the efficiency of the `match_node` method.

    :param graph: The BGraph to filter
    :return: A list of graph nodes representing source file.
    """
    return [node for node in graph if get_node_type(node) == "source"]


def find_target(
    graph: nx.DiGraph,
    source: str,
    return_types: List[str] = DEFAULT_TYPES,
    radius: Optional[int] = None,
) -> Tuple[str, List[str]]:
    """Given a source file, find all dependent targets.

    This is a bit trickier as the source file may be given with an incomplete path.
    However, we don't want to give absurds results, so if more than 1 file matches, an
    error is raised.

    TODO(dm):
        - Intersect for multiple sources files
        - Better handling of return types

    :param graph: The graph to search
    :param source: Source file name
    :param return_types: Optional. List of types to consider as valid types
    :param radius: Optional. How far should the graph go.
        Default is None : consider all the dependencies. A positive integer will reduce
        to node at at most `radius` distance.
    :return: A tuple with the exact match and the list of results
    """
    graph_srcs: List[str] = get_graph_srcs(graph)
    try:
        matched_node = match_node(graph_srcs, source)
    except (bgraph.exc.BGraphNodeNotFound, bgraph.exc.BGraphTooManyNodes) as e:
        logger.info("Failed to find node with error %s", e)
        return "", []

    subgraph = nx.generators.ego_graph(graph, matched_node, center=False, radius=radius)
    results = [
        node
        for node in subgraph
        if any(
            node_type in return_types
            for node_type in get_node_type(graph.nodes[node], all_types=True)
        )
    ]

    return matched_node, results


def find_dependency(graph: nx.DiGraph, origin: str) -> List[str]:
    """Resolve dependencies in a graph.

    Given an origin (which is *not* a source file), find all dependents targets

    :param graph: Graph to search
    :param origin: Origin of the query
    :return: A list of dependent target
    """

    if origin not in graph:
        logger.error("Origin not found %s", origin)
        return []

    # Get dependencies in the graph
    subgraph = nx.generators.ego_graph(graph, origin, radius=None, center=True)
    other_subgraph = nx.generators.ego_graph(
        graph.reverse(), origin, center=True, radius=None
    )

    return list(set(subgraph).union(set(other_subgraph)))


def find_sources(graph: nx.DiGraph, target: str) -> List[str]:
    """Find the sources of target.

    Recursively in the graph, search for all sources files of a target (or a target
     dependencies).

    TODO(dm):
        For conditionals, there may also exists precomputed binaries as the target.
        Find a way to deal with those

    :param graph: Graph yo search
    :param target: Origin of the query (final target)
    :return: A list of source files
    """
    if target not in graph:
        return []

    subgraph = nx.generators.ego_graph(
        graph.reverse(), target, radius=None, center=False
    )
    dependencies = [
        node for node in subgraph if next(subgraph.successors(node), None) is None
    ]

    # Filtering step: since we don't understand conditionals (yet), filter out bogus
    # dependencies
    # TODO(dm)

    return dependencies
