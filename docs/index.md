# BGraph

## Overview
`BGraph` (for `Build-Graphs`) is a project aimed at create build graphs from _blueprints_ in AOSP and querying those graphs.

In short, this project builds/uses Unified Dependency Graph for the [Android Open Source Project](https://source.android.com/) by parsing and linking modules 
defined in the Android build system [Soong](https://source.android.com/setup/build). 

### Use-cases

You should use this tool if you want to find:

* all the dependencies of a source file in AOSP; 
* all the sources involved in the building of a target in AOSP;
* common dependencies between two targets.


## Usage (short)

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
```bash
pip install bgraph
```

See [Installation](installation.md) for more detailed information or other options.

## Citation
This tool is the companion of the SSTIC Presentation (TODO(dm) REF)
If you want to cite it, you may use the following bibtex.

```text
@
```