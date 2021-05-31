# Docker usage (experimental)

A `Dockerfile` is available in `docker/` directory. It has not been properly tested but should still work.

## Content
The container will have all the dependencies required to build `BGraphs` including :
- git v2.29
- repo
- BGraph itself

## Building
```bash
$ docker build -f docker/Dockerfile -t bgraph .
```

This step will take some times because it will download and compile a few components (like git).

!!! note
    By default, the container will stop at the last image. You may add the `--target` parameter to stop at earlier stages.

## Usage
```bash
$ docker run bgraph
```

## Building BGraph inside Docker (untested)

!!! note
    The builder inside the container needs a valid `gitconfig` file. 
    An option is to copy the one used in the system (usually in `$HOME/.git/config`).

```bash
$ docker run \
    --rm \
    -v $(pwd)/graphs:/home/user/graphs \ # To retrieve the generated graph
    -v $XDG_CONFIG_DIR/git/config:/home/user/.gitconfig \ # User/Email should be defined
    bgraph:latest \ # Image name
    bgraph generate-single graphs/ android-10.0.0_r2 'https://android.googlesource.com'
```
