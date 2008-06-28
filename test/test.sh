#!/bin/bash
blender -b  $1 -P ../osgexport-0.1.py --osg="filename=$2"
