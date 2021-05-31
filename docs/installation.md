# Pre-requistes

`BGraph` is divided in two components: the builder and the viewer.

### Viewer dependencies:
- python3.8

### Builder dependencies
- git (v22+): since partial checkouts are used, a modern version of git is needed. The project has been tested with Git 2.29.
- [repo](https://gerrit.googlesource.com/git-repo/+/refs/heads/master/README.md): Google project to query AOSP repository . See the installation instruction from Google.
- A [repo client](https://source.android.com/setup/build/downloading#initializing-a-repo-client).
- Optional: An [AOSP mirror](https://source.android.com/setup/build/downloading#using-a-local-mirror) to have a faster building time.

The mirror is not necessary, but it reduces the number of requests to Google servers.

!!! tip
    An alternative way to install repo is to use the one packaged for your distribution, but it is not recommended.

# Installation

!!! tip
    Install `BGraph` in a virtualenv.


## With pip

```bash
pip install bgraph
```

## With poetry 
!!! note
    [Poetry](https://python-poetry.org/) is a python packaging and dependency manager

```bash
$ git clone gitlab@gitlab.qb:achallande/bgraph.git
$ cd bgraph
$ poetry install --no-dev
```


# Checks (for building)
```bash
$ mkdir android-current && cd android-current
$ repo init -u https://android.googlesource.com/platform/manifest -c --depth=1 --partial-clone --clone-filter=blob:none 
```

If this commands succeeded, you are good to go!
