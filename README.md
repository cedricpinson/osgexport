Status - DISCONTINUED

Follow instruction from github to get the repository

https://github.com/cedricpinson/osgexport

## Installation (blender 2.7+)

To install last version of the exporter go in user preference, then 'Install from File' in the Add-ons tab with the zip from https://github.com/cedricpinson/osgexport/releases

## Command line usage

`osgexport` needs to inject the path to exporter modules into PYTHONPATH. The injection is done by reading the value of the `BlenderExporter` environment variable (see [\_\_init\_\_.py](https://github.com/cedricpinson/osgexport/blob/master/exporter/osg/__init__.py#L46-51)).

```shell

$ BlenderExporter="/path-to-osgexport/blender-2.5/exporter" \
    blender -b "input.blend" \
    -P "${BlenderExporter}/osg/__init__.py" \
    -- --output="output.osgt" \
    [--apply-modifiers] [--enable-animation] [--json-materials] [--enable-animation] \
    [--bake-all] [--bake-quaternions]
```

## How to report a bug

Open an [issue](https://github.com/cedricpinson/osgexport/issues/new) and send a minimal blender file that produce the problem.


## Tests

To run tests:

```shell

mkdir tests && cd tests
cmake ../ -DBLENDER:FILEPATH="/my/path/to/blender" -DTEST=ON
make  # runs test building osgt files for models in blender-2.xx/data/
make test  # runs python test located in blender-2.xx/test/

```

To troubleshoot python tests:  `ctest --debug` or `ctest --output-on-failure`
