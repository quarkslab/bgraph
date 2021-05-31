import networkx  # type: ignore
import rich.table
import rich.box
import rich.console
import json
from pathlib import Path
import pydot  # type: ignore
import typer

from bgraph.types import (
    OutChoice,
    QueryType,
    List,
    Union,
    Tuple,
    Dict,
    NodeType,
    ResultDict,
)
import bgraph.viewer
import bgraph.exc


def format_result(
    graph: networkx.DiGraph,
    results: List[str],
    query: QueryType,
    query_value: str,
    out_choice: OutChoice,
) -> None:
    """Format the result of the viewer.

    :param graph: BGraph
    :param results: Results for the query
    :param query: Type of the query
    :param query_value: Query value
    :param out_choice: Out format
    """

    format_methods = {
        out_choice.TXT: format_text,
        out_choice.JSON: format_json,
        out_choice.DOT: format_dot,
    }

    return format_methods[out_choice](graph, results, query, query_value)


def format_text(
    graph: networkx.DiGraph, results: List[str], query: QueryType, query_value: str
) -> None:
    """Format the results for text consumption (default value).

    Use rich to do some pretty formatting.

    :param graph: BGraph
    :param results: Results for the query
    :param query: Type of the query
    :param query_value: Query value
    """
    table = rich.table.Table(box=rich.box.MINIMAL_DOUBLE_HEAD)

    if query == QueryType.TARGET:
        table.title = f"Sources for the target {query_value}"
        table.add_column("Filename", justify="left")
        table.add_column("File type", justify="right")

        for result in results:
            table.add_row(result, Path(result).suffix)

    elif query == QueryType.DEPENDENCY:
        table.title = f"Dependencies for the target {query_value}"
        table.add_column("Dependency")
        table.add_column("Type")
        table.add_column("Ascending")

        for result in sorted(results):

            ascending = (
                ":heavy_check_mark:"
                if networkx.has_path(graph, result, query_value)
                else ":heavy_multiplication_x:"
            )
            table.add_row(
                result, bgraph.viewer.get_node_type(graph.nodes[result]), ascending
            )

    elif query == QueryType.SOURCE:
        table.title = f"Dependencies for source file {Path(query_value).name}"
        table.add_column("Target")
        table.add_column("Type")
        table.add_column("Distance")

        # Generate the graph to compute the distance
        # Since the graph is much simpler than the original one, it is easier to compute
        # the distance inside this one.
        generated_graph: networkx.DiGraph = networkx.generators.ego_graph(
            graph, query_value, center=True, radius=None
        )

        row_results: List[Tuple[str, NodeType, int]] = [
            (
                result,
                bgraph.viewer.get_node_type(graph.nodes[result]),
                networkx.algorithms.shortest_path_length(
                    generated_graph, query_value, result
                ),
            )
            for result in results
        ]

        for result, node_type, distance in sorted(row_results, key=lambda x: x[2]):
            table.add_row(result, node_type, f"{distance}")

    console = rich.console.Console()
    console.print(table)


def format_dot(
    graph: networkx.DiGraph, results: List[str], query: QueryType, query_value: str
) -> None:
    """Output result as DOT.

    :param graph: BGraph
    :param results: Results for the query
    :param query: Type of the query
    :param query_value: Query value
    """

    if query == QueryType.SOURCE:
        subgraph = networkx.generators.ego_graph(
            graph, query_value, center=True, radius=None
        )
    elif query == QueryType.TARGET:
        subgraph = networkx.generators.ego_graph(
            graph.reverse(), query_value, center=True, radius=None
        )
    elif query == QueryType.DEPENDENCY:
        subgraph = graph.subgraph(results)
    else:
        raise NotImplementedError("Not implemented yet")

    pydot_graph = networkx.nx_pydot.to_pydot(subgraph)

    # Clean data
    for node in pydot_graph.get_nodes():
        try:
            del node.obj_dict["attributes"]["data"]
        except KeyError:
            pass

    try:
        target = pydot_graph.get_node(pydot.quote_if_necessary(query_value))[0]
    except IndexError:
        raise bgraph.exc.BGraphNodeNotFound("Unable to find node")

    target.set_shape("box")
    target.set_color("red")

    typer.echo(pydot_graph)


def format_json(
    graph: networkx.DiGraph, results: List[str], query: QueryType, query_value: str
) -> None:
    """Output the result as JSON

    :param graph: BGraph
    :param results: Results for the query
    :param query: Type of the query
    :param query_value: Query value
    """

    query_dict = {
        QueryType.TARGET: ["target", "Search sources for a target"],
        QueryType.SOURCE: ["sources", "Search target for a source"],
        QueryType.DEPENDENCY: ["dependency", "Search dependencies for a target"],
    }

    result_dict: ResultDict = {}
    if query == QueryType.TARGET:
        result_dict["sources"] = results
    elif query == QueryType.DEPENDENCY or query == QueryType.SOURCE:
        result_dict["target"] = []
        for result in results:
            result_dict["target"].append(
                (result, bgraph.viewer.get_node_type(graph.nodes[result]))
            )

    typer.echo(
        json.dumps(
            {
                "_meta": {
                    "query": query_dict[query][0],
                    "desc": query_dict[query][1],
                    "query_value": query_value,
                },
                "result": result_dict,
            },
            indent=True,
        )
    )
