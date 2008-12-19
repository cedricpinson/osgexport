import os
import Blender
import osg
import osgconf

HELPINFO = (
	"Tip 1. Make sure that....",
	"Tip 2. Make sure that....",
	"Tip 3. Make sure that....",
	"Tip 4. Make sure that....",
	"Tip 5. Make sure that....",
	"Tip 6. Make sure that...."
)

class AnimTKGUIObject(object):
	def __init__(self, val, eventID):
		object.__init__(self);

		self.eventID  = eventID
		self.val      = val
		self.gui      = None
		self.callback = lambda *a, **k: None

	def matchAndUpdate(self, eventID):
		if self.eventID == eventID:
			try:
				self.val = self.gui.val

			except:
				pass
	
			self.callback()

class AnimTKGUI(object):
	def __init__(self, callback=lambda *a, **k: None):
		object.__init__(self)

		self.lastCoords  = [0] * 4
		self.nextEventID = 0
		self.callback    = callback
		self.objects     = {}

	def getNextCoords(self, width, height, stayHoriz=False):
		coords = self.lastCoords

		# If the user wants to stay on the same row.
		if stayHoriz:
			coords[0] += coords[2] + 2

		# Otherwise, increment Y so that we're on a new row.
		else:
			coords[0] = 2
			coords[1] += coords[3] + 2

		# Set the new width/height, and copy it back into the member.
		coords[2 : 1] = [width + 2, height + 2]

		self.lastCoords = coords

		return coords

	def addGUIObject(self, val, initial=None):
		if not self.objects.has_key(val):
			self.objects[val] = AnimTKGUIObject(initial, self.nextEventID)
			
			self.nextEventID += 1

		return self.objects[val]

	def addString(self, val, label, hint="", initial="", stayHoriz=False, w=300, h=24):
		c = self.getNextCoords(w, h, stayHoriz)
		o = self.addGUIObject(val, initial)

		o.gui = Blender.Draw.String(
			"%s: " % label,
			o.eventID,
			c[0], c[1], c[2], c[3],
			o.val,
			255,
			hint
		)

	def addToggle(self, val, label, hint="", initial=False, stayHoriz=False, w=200, h=24):
		c = self.getNextCoords(w, h, stayHoriz)
		o = self.addGUIObject(val, initial)

		o.gui = Blender.Draw.Toggle(
			label,
			o.eventID,
			c[0], c[1], c[2], c[3],
			o.val,
			hint
		)

	def addNumber(self, val, label, minv, maxv, hint="", initial=0, stayHoriz=False, w=300, h=24):
		c = self.getNextCoords(w, h, stayHoriz)
		o = self.addGUIObject(val, initial)

		if initial < minv:
			initial = minv

		o.gui = Blender.Draw.Number(
			"%s: " % label,
			o.eventID,
			c[0], c[1], c[2], c[3],
			o.val,
			minv,
			maxv,
			hint
		)

	def addPushButton(self, val, label, hint="", stayHoriz=False, w=175, h=24):
		c = self.getNextCoords(w, h, stayHoriz)
		o = self.addGUIObject(val, None)

		o.gui = Blender.Draw.PushButton(
			label,
			o.eventID,
			c[0], c[1], c[2], c[3],
			hint
		)

	def InterfaceDraw(self):
		Blender.BGL.glClear(Blender.BGL.GL_COLOR_BUFFER_BIT)
		Blender.BGL.glEnable(Blender.BGL.GL_BLEND)
		Blender.BGL.glBlendFunc(
			Blender.BGL.GL_SRC_ALPHA,
			Blender.BGL.GL_ONE_MINUS_SRC_ALPHA
		)

		# Reset out coordiate "counter."
		self.lastCoords = [0] * 4

		self.addPushButton("help", "Help", w=96)
		self.addPushButton("cancel", "Cancel", w=98, stayHoriz=True)
		self.addPushButton("write", "Write", w=98, stayHoriz=True)
		self.addString("AUTHOR", "Author's Name")
		self.addToggle("LOG", "Create Logfile")
		self.addToggle("SELECTED", "Only Exported Selected")
		self.addToggle("VIEWERFILE", "...", w=150)
		self.addToggle("RELATIVE", "Relative", w=46, stayHoriz=True)
		self.addNumber("INDENT", "Indentation Size", 1, 8, initial=3)
		self.addNumber("FLOATPRE", "Float Precsion", 1, 8, initial=4)
		self.addNumber("ANIMFPS", "Animation FPS", 1, 60, initial=25)

		# Set our callbacks...
		self.objects["help"].callback   = lambda: self.RegisterHelp()
		self.objects["cancel"].callback = lambda: Blender.Draw.Exit()
		self.objects["write"].callback  = lambda: self.Write()
	
		# It does not work for me because Blender.Get("scriptsdir") returns
		# /usr/share/blender/scripts, so first try in user script dir, and if not found
		# try in scriptdir
		try:
			img = Blender.Image.Load(
				os.path.join(Blender.Get("uscriptsdir"), "animtk", "logo.png")
			)
	
                        Blender.Draw.Image(img, 210, 54)

		except:
                        pass

		Blender.BGL.glDisable(Blender.BGL.GL_BLEND)

	def HelpInfoDraw(self):
		Blender.BGL.glClear(Blender.BGL.GL_COLOR_BUFFER_BIT)

		self.lastCoords = [0] * 4

		self.addPushButton("helpback", "Return To Exporter")

		for i, hi in enumerate(HELPINFO[::-1]):
			Blender.Draw.Label(hi, 5, 30 + (i * 22), 500, 20)

		self.objects["helpback"].callback = lambda: self.Register()

	def InterfaceEvent(self, event, value):
		if event == Blender.Draw.ESCKEY:
			Blender.Draw.Exit()

	def InterfaceButton(self, event):
		for k, v in self.objects.iteritems():
			v.matchAndUpdate(event)

	def Register(self):
		Blender.Draw.Register(
			self.InterfaceDraw,
			self.InterfaceEvent,
			self.InterfaceButton
		)

	def RegisterHelp(self):
		Blender.Draw.Register(
			self.HelpInfoDraw,
			self.InterfaceEvent,
			self.InterfaceButton
		)

	def Write(self):
		def CallCallback(path):
			config = osg.parseArgs(["""--osg=
				AUTHOR     = %s;
				LOG        = %s;
				SELECTED   = %s;
				INDENT  = %s;
				FLOATPRE   = %g;
				ANIMFPS    = %s;
				FILENAME   = %s;
			""" % (
				self.objects["AUTHOR"].val,
				self.objects["LOG"].val,
				self.objects["SELECTED"].val,
				self.objects["INDENT"].val,
				self.objects["FLOATPRE"].val,
				self.objects["ANIMFPS"].val,
				path
			)])

			self.callback(config)
	
		Blender.Window.FileSelector(CallCallback, "Export AnimTK", "")
		Blender.Draw.Exit()
