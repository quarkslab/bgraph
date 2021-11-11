import pickle
import pathlib

import bgraph.exc
from bgraph.types import Union, BGraph


def load_graph(graph_path: Union[str, pathlib.Path]) -> BGraph:
    """Load a B-Graph and return the DiGraph associated.

    :param graph: Path to the graph file (stored with pickle)
    :return: A DiGraph
    """
    try:
        graph: BGraph = pickle.load(open(graph_path, "rb"))
    except (pickle.PickleError, FileNotFoundError):
        raise bgraph.exc.BGraphLoadingException("Unable to load the graph.")

    return graph
