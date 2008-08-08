#!/bin/bash
set -x
cur=$(pwd)
cd ../../
blender -b  samples/template.blend -S "Player" -P osgexport.py --osg="filename=${cur}/template_result.osg" 
cd ${cur}
diff template_result.osg check_template_result.osg
