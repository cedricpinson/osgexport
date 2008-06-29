#!/bin/bash
cd ../
blender -b  samples/template.blend -S "Player" -P osgexport-0.1.py --osg="filename=template_result.osg" 
