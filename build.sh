cd blender-2.5/exporter/
version=$(cat osg/__init__.py | grep 'VERSION' | sed 's/VERSION.*"\(.*\)"/\1/')
appname=osgexport-$version
echo $appname
zip -r ../build/${appname}.zip . -i \*.py
