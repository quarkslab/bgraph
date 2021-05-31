"""
Author: dm (achallande@quarkslab.com)

Create source maps for AOSP.

Prerequistes:
    - a recent git version (>2.20)
    - an AOSP mirror
    - time

"""


import os
import logging
import multiprocessing
import pathlib
import tempfile
import functools
import fnmatch
from pathlib import Path
import pickle
import shutil

import sh  # type: ignore
import bgraph
import bgraph.utils
from bgraph.types import List, Dict, Tuple, Optional, Union


"""Logger"""
logger: logging.Logger = bgraph.utils.create_logger(__name__)


def get_all_branches(
    manifest: Union[Path, str], pattern: str = "android-*"
) -> List[str]:
    """Parses the list of all branches available in the mirror directory

    This methods works for both a local manifest directory and a remote url.

    :param manifest A link or a path to the manifest
    :param pattern A pattern to match tags in the remote directory.
    :return: A list of manifest branches
    """

    if type(manifest) is str:
        manifest = f"{manifest}/platform/manifest"
    elif isinstance(manifest, pathlib.Path):
        manifest = manifest / "platform" / "manifest.git"

    try:
        tags = sh.git("ls-remote", "--tag", f"{manifest!s}", pattern)
    except sh.ErrorReturnCode:
        raise bgraph.exc.BGraphManifestException("Unable to retrieve the branches.")

    branches: List[str] = []
    for line_encoded in tags.stdout.splitlines():
        try:
            _, tag = line_encoded.decode().split("\t")
        except ValueError:
            continue

        if tag.startswith("refs/tags/") and not "^" in tag:
            branches.append(tag[len("refs/tags/") :])

    return branches


def create_manifest_branch(
    root_dir: Path, mirror: Union[str, Path], branch_name: str
) -> Path:
    """Create a manifest branch in the root_dir with the manifest branch as name.

    :param root_dir: Where to download the branch
    :param mirror: Path/Link to the mirror directory or manifest URL
    :param branch_name: Name of the branch to checkout
    :raises BGraphBuilderException if repo command is not found
    :return: A path towards the branch work directory
    """

    branch_dir = root_dir / branch_name
    branch_dir.mkdir(exist_ok=True)

    # Init mirror
    if type(mirror) is str:
        # If it is a remote url
        manifest = f"{mirror}/platform/manifest"
    elif isinstance(mirror, pathlib.Path):
        manifest = str(mirror / "platform" / "manifest.git")

    try:
        repo = sh.Command("repo").bake("--color=never")
    except sh.CommandNotFound:
        logger.error("Did not find repo command. Is it in PATH?")
        raise bgraph.exc.BGraphBuilderException("Repo not found.")

    try:
        repo.init(
            "-u",
            f"{manifest!s}",
            "-b",
            branch_name,
            "--partial-clone",
            "--clone-filter=blob:none",
            "--depth=1",
            _cwd=branch_dir,
        )
    except sh.ErrorReturnCode:
        logger.error(
            "Unable to init the repository. Verify that the mirror is correct."
        )
        raise bgraph.exc.BGraphBuilderException("Repo init failed.")

    return branch_dir


def partial_checkout(
    branch_name: str, project_path: Path, git_dir: Union[Path, str]
) -> bool:
    """Performs a partial checkout using git.

    A partial checkout allows to checkout only interesting files and not the whole repository.
    This is a bit tricky and needs a recent git version (>2.22)

    :param branch_name: Name of the branch
    :param project_path: Path where to do the checkout
    :param git_dir: Url/Path to the git directory
    :return: Boolean for success
    """

    # Guard to not redo the operation if the checkout has already been done
    if project_path.is_dir():
        return True

    project_path.mkdir(parents=True, exist_ok=True)

    # Prepare the git command
    git = sh.git.bake(_cwd=project_path)

    # Init the directory only if .git folder is not present because git init fails on already inited git directories
    if not (project_path / ".git").is_dir():
        git.init()
        git.remote("add", "origin", f"{git_dir!s}")

    # Partial fetch : without objects
    try:
        git.fetch(
            "--filter=blob:none",
            "--recurse-submodules=yes",
            "--no-tags",
            "--depth=1",
            "origin",
            "tag",
            branch_name,
        )
    except sh.ErrorReturnCode:
        logger.error("Unable to do the fetch part of the operation.")
        return False

    # Some versions of git will fails if the .git/info/sparse-checkout is already there
    try:
        git("sparse-checkout", "init")
    except sh.ErrorReturnCode:
        pass

    # Sparse checkout magic
    try:
        git("sparse-checkout", "set", "**/*.bp")
        git("sparse-checkout", "reapply")
        git.checkout("--quiet", f"refs/tags/{branch_name}")
    except sh.ErrorReturnCode:
        logger.error("Unable to perform sparse-checkout magic.")
        return False

    # List all the files of the project (without downloading them)
    try:
        result = git("ls-tree", "-r", "--name-only", f"{branch_name}")
        files = result.stdout.decode().split()
    except sh.ErrorReturnCode:
        files = []

    # We will need the list of files afterwards so store it
    try:
        pickle.dump(files, open(project_path / "files.pickle", "wb"))
    except pickle.PickleError:
        logger.error("Unable to dump the list of files in the pickle-file.")
        return False

    # Save local space: delete git folder
    local_dir = project_path / ".git"
    if local_dir.is_dir():
        shutil.rmtree(local_dir)

    return True


@bgraph.utils.no_except
def project_checkout(
    branch_name: str,
    branch_dir: Path,
    mirror: Union[str, Path],
    paths: Tuple[Path, Path],
) -> None:
    """Perform a project checkout.

    The project name is where a project is found in the mirror (e.g. MIRROR/platform/external/sqlite)
    The relative project path is the final path of the project in AOSP (e.g. ROOT/external/sqlite)

    Abort fast if no git directory is found in the mirror

    :param branch_name: Name of the branch to checkout
    :param branch_dir: Branch working directory
    :param mirror: Path/Link to a mirror
    :param paths: Project Name and project relative path
    :return:
    """
    project_name, relative_project_path = paths

    # Mirror git dir
    if type(mirror) is str:
        git_dir = f"{mirror}/{project_name}"
    elif isinstance(mirror, pathlib.Path):
        git_dir = str(mirror / f"{project_name}.git")

    # AOSP project dir
    project_path = branch_dir / relative_project_path

    if isinstance(git_dir, Path) and not git_dir.is_dir():
        logger.error("Project not found (%s)", git_dir)
        return

    partial_checkout(branch_name, project_path, git_dir)


def combine_files_path(branch_dir: Path) -> Dict[Path, List[str]]:
    """Load the "files.pickle" stored with results of git commands.

    :param branch_dir: Directory to find the AOSP partial tree
    :return: A mapping of path and the list of files inside the project
    """
    files: Dict[Path, List[str]] = {}
    for file_path in branch_dir.rglob("files.pickle"):
        try:
            local_files = pickle.load(open(file_path, "rb"))
        except pickle.PickleError:
            continue

        files[file_path.parent] = local_files

    return files


def clean_disk(branch_workdir: Path) -> None:
    """Remove a branch directory on the disk to save some space

    :param branch_workdir: Path to the directory to remove
    """
    if branch_workdir.is_dir():
        shutil.rmtree(branch_workdir, ignore_errors=True)


@bgraph.utils.no_except
def compose_manifest_branch(
    branch_name: str,
    mirror: Union[str, Path],
    work_dir: Optional[Path] = None,
    force: bool = False,
) -> Optional[Path]:
    """Create the soong parser for a manifest branch.

    As the process is slow, multiprocessing.Pool is used to speed the checkout.
    The bottleneck is the parsing of blueprints files. However, since variables
    definition must be analyzed, we cannot just randomly parallelize this step and
    it must be done carefuly (read: it's not done yet.).

    The SoongParser is used to parse the whole tree blueprints files and stored using
    pickle. Another step is to convert this object as a (networkx) graph.

    :param branch_name: Name of the branch to checkout
    :param mirror: Path/Link towards the mirror or the manifest URL
    :param work_dir: Optional. Working directory - if not set, a temporary folder is used
    :param force: Optional. Overwrite existing branch.
    :return: The path to the work dir
    """
    logger.info("Start composing for %s", branch_name)

    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="bgraph_"))

    # Guard: do not redo a branch
    pickle_file = work_dir / f"{branch_name}.pickle"
    if pickle_file.is_file() and force is False:
        logger.info("Branch already found; skip.")
        return work_dir
    elif (work_dir / f"{branch_name}.empty").is_file():
        logger.info("Branch empty; skip.")
        return work_dir

    # Create a branch by using repo
    try:
        branch_dir = create_manifest_branch(work_dir, mirror, branch_name)
    except bgraph.exc.BGraphBuilderException:
        return None

    manifest_file = branch_dir / ".repo" / "manifests" / "default.xml"

    logger.info("List projects")
    project_checkout_branch = functools.partial(
        project_checkout, branch_name, branch_dir, mirror
    )

    # Load the manifest
    manifest = bgraph.parsers.Manifest.from_file(manifest_file)

    # Core: multiprocessing
    with multiprocessing.Pool() as pool:
        res = pool.map_async(project_checkout_branch, manifest.get_projects().items())
        res.get(24 * 60 * 60)

    logger.info("Finished to compose with %s", branch_name)

    # Guard: Search build files
    for _ in branch_dir.rglob("Android.bp"):
        break
    else:
        logger.info("Found 0 Android.bp file, aborting")

        # Create an empty file to prevent from doing it if we restart
        with open(work_dir / f"{branch_name}.empty", "w") as _:
            pass

        clean_disk(branch_dir)
        return work_dir

    soong_parser = bgraph.parsers.SoongParser()

    logger.info("Starting parsing AOSP build files")
    soong_parser.parse_aosp(branch_dir, project_map=manifest.get_projects())
    soong_parser.file_listing = combine_files_path(branch_dir)

    # Save the result
    try:
        pickle.dump(soong_parser, open(pickle_file, "wb"))
    except pickle.PickleError:
        logger.error("Failed to pickle")
        clean_disk(branch_dir)
        return work_dir

    # Clean the disk
    logger.info("Clean branch")
    clean_disk(branch_dir)

    return work_dir


def compose_all(
    mirror: Union[str, Path],
    branch_pattern: str = "android-*",
    work_dir: Optional[Path] = None,
    force: bool = False,
) -> Path:
    """Iterates through all the branches in AOSP and create the source maps.

    This methods:
        - list all the existing branches and filter those matching the pattern
        - does a partial checkout of each of them
        - parses the Soong File and store them

    :param mirror: Path/Link to a mirror directory or an URL.
    :param branch_pattern: Optional. Pattern to filter branches
    :param work_dir: Optional. Work directory
    :param force: Optional. Overrides results.
    :return: The path to the work directory
    """

    # List branches
    all_branches = get_all_branches(mirror)
    branches = fnmatch.filter(all_branches, branch_pattern)

    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="bgraph_"))

    logger.info("Found %d branches", len(branches))
    for branch_name in branches:
        compose_manifest_branch(branch_name, mirror, work_dir, force)

    logger.info("Finished")

    return work_dir
