# Roadmap / improvements ideas

!!! note
    This list of features / improvements is more a wishlist than anything else. Do not expect them to be implemented 
    soon or ever.

## Meta
* Change BGraph format from pickle to protobuf
* Code refactoring for decoupling soong parser
* Improve documentation

## Parsers
### Soong Parser
* Namespaces support
* Filegroup support
* Automatic types discovery
* Better handling of dependencies link (and support for `exclude_`)

## Android.mk
* Add an Android.mk parser (or use `androidmk` to convert Android.mk)

## UX
* Improve options for text formatting (sorting, filtering)