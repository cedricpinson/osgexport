cd blender-2.5/exporter/
version=$(cat osg/__init__.py | grep '"version":' | sed 's/.*(\([0-9]*\),\([0-9]*\),\([0-9]*\).*/\1.\2.\3/' )
appname=osgexport-$version
echo $appname
zip -r ../build/${appname}.zip . -i \*.py
