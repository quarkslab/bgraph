import pickle
import pathlib
import networkx  # type: ignore

import bgraph.exc
from bgraph.types import Union, BGraph


def load_graph(graph: Union[str, pathlib.Path]) -> BGraph:
    """Load a B-Graph and return the DiGraph associated.

    :param graph: Path to the graph file (stored with pickle)
    :return: A DiGraph
    """
    try:
        bgraph: BGraph = pickle.load(open(graph, "rb"))
    except (pickle.PickleError, FileNotFoundError):
        raise bgraph.exc.BGraphLoadingException()

    return bgraph
