#!/bin/bash
blender -b  ../samples/template.blend -P ../osgexport-0.1.py --osg="filename=template_result.osg"
