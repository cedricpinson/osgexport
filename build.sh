cd exporter/
version=$(cat osg/__init__.py | grep '"version":' | sed -e 's/[a-zA-Z "():]*//g' -e 's/,$//g' -e 's/,/-/g')
appname=osgexport-$version
echo $appname
zip -r ../build/${appname}.zip . -i \*.py
