# Limitations and frequent errors

## Soong parsing is not complete

The parsing of _blueprints_ files is not complete, and some features are not supported (like soong_namespaces.)


## Dependency is wrong/missing/incomplete

There are some cases when the dependency is bogus:

* it uses an unsupported feature of Soong (please open an issue to let us know)
* the module is still uses `Android.mk` files: nothing to do (or implement a `Android.mk` parser)
* there is a bug in `BGraph`: please open an issue with enough details so we can reproduce it
