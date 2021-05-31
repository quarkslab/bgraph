"""
Author: dm

Collection of dirty scripts used to generate a source graph for AOSP based on the parsing of the Android.bp (blueprints) files.

This must be used with the SoongParser developed in AOSP_BUILD project (aka acb)
"""

from pathlib import Path
import pickle
import fnmatch
import multiprocessing
import functools

import networkx as nx  # type: ignore

import bgraph.parsers.soong_parser
import bgraph.utils
from bgraph.types import Iterable, Dict, List, Tuple, Literal, Optional, Section


"""In Soong files, keys what indicates dependencies between targets"""
dependencies_keys: List[str] = [
    "shared_libs",
    "static_libs",
    "header_libs",
    "whole_static_libs",
    "required",
    "system_shared_libs",
]

"""In soong files, keys that indicates a source dependency"""
srcs_keys = [
    "srcs",
    "include_dirs",
    "local_include_dirs",
    "export_include_dirs",
]


logger = bgraph.utils.create_logger(__name__)


def compute_file_list(
    section_files: Dict[Path, List[str]],
    soong_file: Path,
    project_path: Path,
    files: List[str],
) -> List[str]:
    """Create the file list that matches the soong_file for the project.

    WARNING: This function is *not* pure, it will modify in-place the section_files
    mapping, allowing for an easy caching.

    :param section_files: A mapping storing the files mapping
    :param soong_file: Path for a soong file
    :param project_path: Path for a project (should be a parent of the soong file)
    :param files: List of files in the project (found via Git)
    :return: A list of files descendent of the soong file in the project
    """
    if soong_file not in section_files:

        section_files[soong_file] = []
        for file in files:
            full_path = project_path / file
            if str(full_path).startswith(str(soong_file)):
                try:
                    section_files[soong_file].append(
                        full_path.relative_to(soong_file).as_posix()
                    )
                except ValueError:
                    pass

    return section_files[soong_file]


def convert_section(
    graph: nx.DiGraph,
    section_files: Dict[Path, List[str]],
    section_name: str,
    section: Section,
    project_files: List[str],
) -> None:
    """Convert a section from the SoongParser into a node in the graph and sets its
    dependencies

    Warning: This functions modifies in place the graph.

    Note: Some refactoring should be done on the file path detection (drop fnmatch).

    TODO(dm):
        Integrate other type of dependencies such as exclusion

    :param graph: The UDG
    :param section_files: A mapping for section files allowing an easy cache
    :param section_name: Name of the section to convert
    :param section: Section data in iteself
    :param project_files: Files found in the source tree
    """
    # Project Path
    try:
        project_path: Path = section[
            bgraph.parsers.soong_parser.SoongParser.SECTION_PROJECT_PATH
        ]
    except KeyError:
        logger.error("Missing section_project_path in %s", section_name)
        return

    # Local Soong files
    try:
        soong_file_path: Path = section[
            bgraph.parsers.soong_parser.SoongParser.SOONG_FILE
        ].parent
    except (KeyError, AttributeError):
        logger.error("Missing soong_file in %s", section_name)
        return

    for key, value in bgraph.utils.recurse(section):  # type: ignore
        edge_type: Optional[Literal["dep", "src"]] = None
        if key in dependencies_keys:
            edge_type = "dep"

        elif key in srcs_keys:
            edge_type = "src"

        if edge_type is not None:
            for dep in value:
                if edge_type == "src":

                    # For dependency key representing directories, add a *
                    if "dirs" in key:
                        dep = f"{dep}*"

                    # Since we are using fnmatch and not a proper tool, we also
                    # must take care of those prefix and remove them...
                    # TODO(dm): Use removeprefix in Python3.9
                    for prefix in ["./", "."]:
                        if dep.startswith(prefix):
                            dep = dep[len(prefix) :]
                            break

                    # Resolve * in dependencies files : the pattern must be
                    # modified to accomodate Python fnmatch module
                    # FIX: https://android.googlesource.com/platform/build/soong/+/refs/heads/master#file-lists

                    for dependency_file in fnmatch.filter(
                        compute_file_list(
                            section_files, soong_file_path, project_path, project_files
                        ),
                        dep.replace("**/", "*"),
                    ):
                        graph.add_edge(
                            str(soong_file_path / dependency_file),
                            section_name,
                            type=edge_type,
                        )
                else:
                    graph.add_edge(dep, section_name, type=edge_type)


def build_source_map(sp: bgraph.parsers.soong_parser.SoongParser) -> nx.DiGraph:
    """
    From a SoongParser object, converts all the targets into a graph representation where
    the links between two nodes are :
        - a dependency link if the origin is induced in the destination
        - a source link if the origin is a source file and the destination a target

    The graphs are saved as networkx objects with pickle.

    :param: sp: The soong parser
    :return: An UDG as a DiGraph
    """
    graph = nx.DiGraph()

    for target in sp.sections:
        graph.add_node(target, data=sp.get_section(target))

    file_listing = sp.file_listing

    section_files: Dict[Path, List[str]] = {}

    nodes = list(graph.nodes)
    for idx, section_name in enumerate(nodes):
        if idx % 500 == 0:
            logger.debug("Converting section %d / %d", idx, len(nodes))

        for section in graph.nodes[section_name]["data"]:

            project_path: Path = section.get(
                bgraph.parsers.soong_parser.SoongParser.SECTION_PROJECT_PATH
            )
            project_files: List[str] = sp.file_listing.get(project_path, [])
            if not project_files:
                logger.info(f"Cannot find files for project {section_name}")

            convert_section(graph, section_files, section_name, section, project_files)

    return graph


def convert_single(result_dir: Path, pickle_file: Path) -> Tuple[str, bool]:
    """Convert a pickle file representing a soong parser to a graph and store it in
    result dir.

    :param result_dir: Where to store the result
    :param pickle_file: Which file to convert
    :return: A tuple (branch_name, boolean for sucess) for later statistics.
    """
    branch_name: str = pickle_file.stem
    bgraph_file = result_dir / (pickle_file.with_suffix(".bgraph").name)

    try:
        soong_parser = pickle.load(open(pickle_file, "rb"))
    except pickle.PickleError:
        return branch_name, False

    graph = build_source_map(soong_parser)

    try:
        with open(bgraph_file, "wb") as file:
            pickle.dump(graph, file)
    except pickle.PickleError:
        return branch_name, False

    return branch_name, True


def convert(pickle_dir: Path, result_dir: Path) -> None:
    """Iterates through the source_maps directory and convert every soong_parser objects
    to a NetworkX DiGraph

    :param pickle_dir: Path towards the file where the pickle files are stored.
    :param result_dir: Path where the BGraph are stored
    """

    to_convert: List[Path] = [
        pickle_file
        for pickle_file in pickle_dir.glob("*.pickle")
        if not (result_dir / (pickle_file.with_suffix(".bgraph").name)).is_file()
    ]
    partial_convert_single = functools.partial(convert_single, result_dir)

    with multiprocessing.Pool() as pool:
        res = pool.map_async(partial_convert_single, to_convert)
        results = res.get()

    count_success = 0
    for branch_name, result in results:
        if result is False:
            logger.info("Fail to convert %s", branch_name)
        else:
            count_success += 1

    logger.info("Converted %d/%d branches", count_success, len(results))
