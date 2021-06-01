"""
Author: dm

The query is : what are the CVE affecting a static_libary in AOSP ?

Methodology:
    1/ Load the list of AOSP vulnerabilities
    2/ Load a modern BGraph (I choose one for android-11);
    3/ For each vulnerability and each file affected by the vulnerability, check if the
        primary target of the file is a static_library.
    4/ Report the results

How to reproduce:
    - Have a list of vulnerability in JSON (an example is given in the demo-cve.json file)
    - Have BGraph installed and a BGraph for android-11.
    - Modern python (3.7+)

Input:
    - A list of CVE in AOSP in the example/all-cve.json

Output:
    - a list of vulnerabilities affecting static library in AOSP

"""
import dataclasses
import json
import networkx  # type: ignore
import pathlib
from typing import Set, List, Any

import bgraph
from bgraph.types import NodeType

BGraph = networkx.DiGraph


@dataclasses.dataclass
class Cve:
    """A CVE"""

    cve_id: str
    component: str
    commit: str
    files: List[str]


class DataclassEncoder(json.JSONEncoder):
    def default(self, o: Any):
        """Allow the encoding of a CVE-dataclass."""
        if isinstance(o, Cve):
            return dataclasses.asdict(o)
        return json.JSONEncoder.default(self, o)


def get_vulnerabilities() -> List[Cve]:
    """Returns a list of CVE."""

    try:
        with open("examples/all-cve.json", "r") as file:
            cves = json.load(file)
    except FileNotFoundError as e:
        print(
            "You must have a cve JSON file."
        )
        raise e

    return [Cve(**cve) for cve in cves]


def find_target_type(graph: BGraph, file_path: str) -> Set[NodeType]:
    """Find the type of targets in a BGraph

    :param graph: BGraph
    :param file_path: Path to a source file
    :return: A set of NodeType
    """
    try:
        _, targets = bgraph.viewer.find_target(graph, file_path, radius=1)
    except bgraph.exc.BGraphException as e:
        # print(f"Failed because {e}")
        return set()

    if not targets or len(targets) > 1:
        # print(f"Failed because targets is {len(targets)}")
        return set()

    return set(bgraph.viewer.get_node_type(graph.nodes[targets[0]], all_types=True))


def has_static_lib_vuln(graph: BGraph, vuln: Cve) -> bool:
    """Check if the vulnerability is a "static" one.

    :param graph: BGraph
    :param vuln: Vulnerability commit from Roy
    :return: Boolean
    """
    affected_types = set()
    for file in vuln.files:
        types = find_target_type(graph, file)
        if types:
            affected_types.update(types)
    return "cc_library_static" in affected_types


def main():
    # Get the recent vulnerabilities
    vulnerabilities: List[Cve] = get_vulnerabilities()

    # From BGraph, load a BGraph for android-11
    graph_path: pathlib.Path = next(pathlib.Path("graphs").glob("android-11*"), None)
    if graph_path is None:
        raise FileNotFoundError("Unable to find a BGraph for Android 11.")

    graph: BGraph = bgraph.viewer.load_graph(graph_path)

    # Filter the list of vulnerabilities by removing the non matching one
    static_vulns = [
        vuln for vuln in vulnerabilities if has_static_lib_vuln(graph, vuln)
    ]

    # Save the result in static-vuln.json
    with open("examples/static-vuln.json", "w") as file:
        json.dump(static_vulns, file, indent=True, cls=DataclassEncoder)
