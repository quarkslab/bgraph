import logging
import pathlib
from pathlib import Path
import enum
import typer

import rich.table
import rich.console
import rich.filesize

import bgraph
import bgraph.exc
import bgraph.utils
from bgraph.types import Optional, QueryType, OutChoice, List, Union


app = typer.Typer()


@app.command(name="generate-single")
def generate_single(
    result_dir: Path = typer.Argument(
        ...,
        help="Where to store the result",
        dir_okay=True,
        exists=True,
        writable=True,
        resolve_path=True,
    ),
    branch_name: str = typer.Argument(
        ..., help="Branch from which generating the BGraph"
    ),
    mirror: str = typer.Argument(
        ...,
        help="Mirror directory for AOSP (either a link or a path)",
    ),
    workdir: Optional[Path] = typer.Option(
        None, help="Workdir", dir_okay=True, writable=True, exists=True
    ),
):
    """Generate a BGraph from a branch.

    It will work in the workdir and store results in result_dir.
    """

    # Assume the mirror is a Path if "http" is not found in mirror.
    mirror_path: Union[str, pathlib.Path] = bgraph.utils.clean_mirror_path(mirror)

    workdir = bgraph.builder.compose_manifest_branch(branch_name, mirror_path, workdir)

    if workdir is None:
        typer.echo("Compose manifest failed.", err=True)
        raise typer.Exit(code=1)

    bgraph.builder.convert(workdir, result_dir)


@app.command()
def generate(
    result_dir: Path = typer.Argument(
        ...,
        dir_okay=True,
        exists=True,
        writable=True,
        resolve_path=True,
        help="Where to store the resulting BGraph",
    ),
    mirror: str = typer.Argument(
        ..., help="Path to the mirror or the URL to AOSP source"
    ),
    branch_pattern: str = typer.Option(
        "android-*", help="Pattern to match the branches"
    ),
    workdir: Optional[Path] = typer.Option(
        None, help="Work directory (default will be a tmp directory)"
    ),
):
    """Generate BGraph's from a mirror dir."""

    mirror_path: Union[str, pathlib.Path] = bgraph.utils.clean_mirror_path(mirror)

    workdir = bgraph.builder.compose_all(mirror_path, branch_pattern, workdir)

    bgraph.builder.convert(workdir, result_dir)
    founds = len(list(result_dir.glob("*.bgraph")))
    typer.echo(f"Generated {founds} graphs.")


@app.command(name="list")
def list_command(
    directory: Path = typer.Argument(
        None,
        file_okay=False,
        dir_okay=True,
        exists=True,
        readable=True,
        resolve_path=True,
        help="The directory to search BGraph files",
    ),
    extension: Optional[str] = typer.Option(
        ".bgraph", help="Extension of the BGraph files"
    ),
):
    """
    List the BGraph already generated.
    """

    table = rich.table.Table(title="BGraph founds :")
    table.add_column("Name", justify="right")
    table.add_column("Size", justify="right")

    for bgraph_file in directory.rglob(f"*{extension}"):

        table.add_row(
            bgraph_file.name, rich.filesize.decimal(bgraph_file.stat().st_size)
        )

    console = rich.console.Console()
    console.print(table)


@app.command()
def query(
    graph_path: Path = typer.Argument(
        ...,
        file_okay=True,
        dir_okay=False,
        exists=True,
        resolve_path=True,
        readable=True,
        help="BGraph to query",
    ),
    target: str = typer.Option(None, help="Target to query"),
    src: str = typer.Option(None, help="Source file"),
    dependency: str = typer.Option(None, "--dep", help="Dependecy"),
    out: OutChoice = typer.Option(OutChoice.TXT, help="Output format"),
):
    """Query a BGraph."""

    defined = [target is not None, src is not None, dependency is not None]
    if defined.count(True) > 1:
        typer.echo("Define only one of src/target/dependency")
        raise typer.Exit(code=1)

    try:
        graph = bgraph.viewer.load_graph(graph_path)
    except bgraph.exc.BGraphLoadingException:
        typer.echo("Unable to load the graph")
        raise typer.Exit(code=1)

    result: List[str]
    query_type: QueryType
    if target is not None:
        result = bgraph.viewer.find_sources(graph, target)
        query_type = QueryType.TARGET
        query_value = target
    elif src is not None:
        query_value, result = bgraph.viewer.find_target(graph, src)
        query_type = QueryType.SOURCE
    else:
        query_type = QueryType.DEPENDENCY
        result = bgraph.viewer.find_dependency(graph, dependency)
        query_value = dependency

    if not result:
        typer.echo("No result for request")
        raise typer.Exit(code=2)

    bgraph.viewer.format_result(graph, result, query_type, query_value, out)


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Activate verbose output"
    )
):
    """BGraph - generate and query build dependency graphes.

    BGraph is used to manipulate build dependency graphs generated from blueprint files.
    The main commands are:

        - generate : used to generates multiples graphs

        - query: used to query a previously generated graph

    To get more help, see the online documentation.
    """
    logging_level = logging.INFO
    if verbose:
        logging_level = logging.DEBUG

    logging.getLogger().setLevel(logging_level)
