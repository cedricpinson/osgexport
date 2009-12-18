import osgconf

VERSION = "0.9.0"
AUTHOR  = "Jeremy Moles, Cedric Pinson"
EMAIL   = "jeremy@emperorlinux.com, cedric.pinson@plopbyte.net"
URL     = "http://www.plopbyte.net, http://hg.plopbyte.net/osgexport"

DOC = """
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

NOTE:

This code is inherited from the project I did (Jeremy) w/ Palle Raabjerg
for a Google SOC project in Cal3D. There may still be some remnants of that
project here, but most of this is SUPERBLY modified.
"""

# A function that will parse the passed-in sequences and set the appropriate
# values in osgconf.
def parseArgs(parse):
	args     = []
	strip    = lambda s: s.rstrip().lstrip().replace("\t", "").replace("\n", "")
	str2bool = lambda s: s.lower() == "true" or s == "1"

	for arg in parse:
		arg = strip(arg)
		# Check and maks sure we're formatted correctly.
		if "--osg" in arg:
			if len(arg) >= 6 and arg[5] == "=":
				args = arg[6 : ].split(";")
			else:
				print "ERROR: OpenSceneGraph format is: --osg=\"filename=foo\""

        argmap = {}
	for arg in args:
		if "=" in arg:
			a, v = arg.split("=")
			a    = strip(a).upper()
			v    = strip(v)

			print "OpenScenGraph Option [", a, "] =", v
			{
				"FILENAME":   lambda: argmap.setdefault(a,v),
				"FLOATPRE":   lambda: argmap.setdefault(a,int(v)),
				"INDENT":  lambda: argmap.setdefault(a,int(v)),
				"ANIMFPS":    lambda: argmap.setdefault(a,float(v)),
				"AUTHOR":     lambda: argmap.setdefault(a,v),
				"BAKE":       lambda: argmap.setdefault(a,v.lower()),
				"LOG":        lambda: argmap.setdefault(a,str2bool(v)),
				"SELECTED":   lambda: argmap.setdefault(a,v),
                                "RELATIVE_PATH": lambda: argmap.setdefault(a,str2bool(v)),
				"FORMATNUM":  lambda: argmap.setdefault(a,int(v)),
                                "OBJECT_SELECTED": lambda: argmap.setdefault(a,v)
			}[a]()

        if len(argmap):
                print argmap
                return osgconf.Config(argmap)
        return None
