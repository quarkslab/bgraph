# Inner workings 

## Methodology

This work creates a Unified Dependency Graph (UDG) for every module found in a root tree of AOSP. The UDG in BGraph is a graph where 
the nodes are either sources files or valid Soong targets. Every node in the graph is linked to all its dependent (either 
because they use them or because they need them).

## Algorithm

The algorithm is roughly described below:

1. Discover every `Android.bp`
1. Parses them as "targets" and store the result
1. Get the list of files in each of the projects and store it
1. Combine every module:
    * Resolve wildcards in blueprint definitions with the list of files of the project
    * Create link for dependency keys in blueprints
1. Save the `bgraph`.


## To go further
See the [paper](https://www.sstic.org/2021/presentation/bgraph/) or the [presentation](https://www.sstic.org/2021/presentation/bgraph/) at SSTIC 2021.
