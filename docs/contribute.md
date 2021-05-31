# Contributing

Welcome! First, many thanks if you are willing to contribute to this project. Everyone is welcome.

## Bird's eye view

`BGraph` and its inner-workings are explained in the [Innerworkings](explanations.md) part of the documentation.

## Code organization

The code is mainly split in three parts.

### Builder

The builder is responsible for the logic around fetching build compilation directives. Today it is tightly coupled with 
AOSP. The graph part of the builder convert a soong file into an Unified Depency Graph.

### Parsers
It is the place where the build compilation directives files are analyzed. Today, only _blueprints_ (Soong configuration 
files) are analyzed. But if you want to add the support for another kind of file, it is the place to go.

!!! note
    Start a Pull Request/Issue **before** starting to work on it as it requires some refactoring in the code.

### Viewer

Everything that deals with the querying and outputting results on `bgraphs` is stored there. 

## For developers

### Testing

There aren't many tests written for the project _yet_, and even most of the Soong Parser isn't properly tested. However, the few tests that are present are runned using the following snippet.

```bash
$ poetry install # To install with dev-dependencies
$ poetry run pytest --cov=bgraph  # To run the tests
```

Contributions are encouraged to add tests.

### Linting

The code follow a strict [black](https://github.com/psf/black) formatting.

To run the linter:
```bash
$ poetry run black src tests
```

### Type check

The code normally pass mypy checks without problems.

```bash
$ poetry run mypy src/
```