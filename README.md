BGraph
======

`BGraph` is a tool designed to generate dependencies graphs from `Android.bp` soong files.

## Overview
`BGraph` (for `Build-Graphs`) is a project aimed at create build graphs from _blueprints_ in AOSP and querying those graphs.

In short, this project builds/uses Unified Dependency Graph for the [Android Open Source Project](https://source.android.com/) by parsing and linking modules 
defined in the Android build system [Soong](https://source.android.com/setup/build). 

### Use-cases

You should use this tool if you want to find:

* all the dependencies of a source file in AOSP; 
* all the sources involved in the building of a target in AOSP;
* common dependencies between two targets.


## Usage
```bash
% bgraph --help                                                       
Usage: bgraph [OPTIONS] COMMAND [ARGS]...

  BGraph - generate and query build dependency graphes.

  BGraph is used to manipulate build dependency graphs generated from
  blueprint files. The main commands are:

      - generate : used to generates multiples graphs

      - query: used to query a previously generated graph

  To get more help, see the online documentation.

Options:
  -v, --verbose         Activate verbose output  [default: False]
  --install-completion  Install completion for the current shell.
  --show-completion     Show completion for the current shell, to copy it or
                        customize the installation.

  --help                Show this message and exit.

Commands:
  generate         Generate BGraph's from a mirror dir.
  generate-single  Generate a BGraph from a branch.
  list             List the BGraph already generated.
  query            Query a BGraph.
```

## Installation

### Using poetry
```bash
poetry install bgraph
```

### Using pip
```bash
pip install bgraph
```

### Using docker
```bash
docker build -f docker/Dockerfile -t bgraph .
```

This will create a container with `git`, `repo` and `bgraph` and will take some time (because it compiles git from the source).

See [Docker](docs/docker.md) for more instructions.

## Prerequisites
- python3.8
  
### Optional dependencies for the builder:
- repo
- git (>25): since we're using partial-checkouts, a modern version of git is required
- at least **1Go** of free disk space
- (Optional: AOSP mirror)

See [Building from AOSP](docs/building.md) for more details.

## Documentation
[Documentation](https://quarkslab.github.io/bgraph)

## Licence
[Apache-2](https://choosealicense.com/licenses/apache-2.0)

## Contributing
Contributions are always welcome!

See the [Contribution](docs/contribute.md) documentation for details on all you need to know about contributing.


## Authors
- dm (achallande@quarkslab.com)
