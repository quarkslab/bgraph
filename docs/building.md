# Generate the graph for a version of AOSP

This small tutorial will help you to generate a BGraph for a specific version of AOSP.

!!! note
    This will assume that you were able to install repo (and it is available in the `$PATH`) and you have access to an AOSP mirror.

## BGraph: generate-single
!!! info
    The generation process needs around ~1/2 Go at peak usage and finished with ~125 Mo.

```bash
% bgraph generate-single --help                                           
Usage: bgraph generate-single [OPTIONS] RESULT_DIR BRANCH_NAME MIRROR

  Generate a BGraph from a branch.

  It will work in the workdir and store results in result_dir.

Arguments:
  RESULT_DIR   Where to store the result  [required]
  BRANCH_NAME  Branch from which generating the BGraph  [required]
  MIRROR       Mirror directory for AOSP (either a link or a path)  [required]

Options:
  --workdir PATH  Workdir
  --help          Show this message and exit.
```

## Example (using AOSP directory)

!!! warning
    This process takes some time (~15 min) and if you have no local mirror, some network bandwidth.

```bash
% bgraph generate-single --workdir /tmp/bgraph graphs/ android-10.0.0_r1 'https://android.googlesource.com'
```

This command creates the BGraph of `android-10.0.0_r1` and store it in `graphs/`. It will use the `/tmp/bgraph` directory to work (must exists first) and will perform a checkout from Google AOSP root tree.

!!!note
    `graphs/` is the output directory in the following examples and must be writable.

## Example (using a local mirror)

If you have an AOSP local mirror mounted in `/mnt/mirror/mirror` and wants to generate the graph for `android-11.0.0_r1`.
```bash
% mkdir graphs # where to store the results
% bgraph generate-single graphs/ android-11.0.0_r1 /mnt/mirror/mirror/
```

At the end, if everything went well, you will find 
```bash
% ls graphs/
android-11.0.0_r1.bgraph
```

This object is a `pickle` file representing a `networkx.DiGraph`.

## Options
* `workdir` : If the option is specified, all the work will be done in the workdir. Otherwise, this will create a new directory in `/tmp`. 
  This is useful if you want to generate multiple BGraphs and want to do them only once (or restart.)
  
## Listing branch
In the example, we asked for generating the BGraph of branch `android-11.0.0_r1` but there exists numerous of them in AOSP tree.

You may find the list of branches on [Google website](https://source.android.com/setup/start/build-numbers#source-code-tags-and-builds)

Or using this command (if you have a local mirror):
```bash
% cd /mnt/mirror/platform/manifest.git
% git branch -a
```

## BGraph: generate

If you want to generate BGraph for multiples branches in AOSP, you can use the `generate` command.
This takes an additional argument `--branch-pattern` which defaults to `android-*` and will restrict the branches built.

```bash
% bgraph generate --help
Usage: bgraph generate [OPTIONS] RESULT_DIR MIRROR

  Generate BGraph's from a mirror dir.

Arguments:
  RESULT_DIR  Where to store the resulting BGraph  [required]
  MIRROR      Path to the mirror or the URL to AOSP source  [required]

Options:
  --branch-pattern TEXT  Pattern to match the branches  [default: android-*]
  --workdir PATH         Work directory (default will be a tmp directory)
  --help                 Show this message and exit.

```

## Troubleshooting

### Many failed to fetch errors

Google rate limits the requests for anonymous user but `BGraph` tries to be as fast as possible by running checkouts on 
multiple cores. A solution to this is to use authentication to Google server, following their guide [here](https://source.android.com/setup/build/downloading#using-authentication).

Finally, assuming you are building inside the container, the command would look like this :
```bash
% docker run --rm \ 
  # Where to store the graphs
  -v $(pwd)/graphs:/home/user/graphs \
  # Git config file
  -v $(HOME)/.gitconfig:/home/user/.gitconfig \
  # Git cookies files
  -v $(HOME)/.gitcookies:/home/user/.git/cookies \
  # Container name and command
  bgraph:latest bgraph generate-single graphs/ 'android-10.0.0_r1' \
  # Use the authenticated mirror
  'https://android.googlesource.com/a'
```

See [Docker](docker.md) for more informations on how to build inside the container.
