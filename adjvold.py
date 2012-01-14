#!/usr/bin/env python

# adjvold -- dbus service for volume adjusting with an optional GTK progressbar
#
# Copyright (C) 2009 Adrian C. <anrxc_sysphere_org>
# Modified by	2011 Seva K. <vs.kulaga_gmail_com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# usage:
# to start service:
#    nohup /path/to/adjvold.py &
# to adjust volume:
#    python -c "import dbus; dbus.SessionBus().get_object('org.volume.VolumeService', '/VolumeService').adjust_volume(-10,False);"
#    python -c "import dbus; dbus.SessionBus().get_object('org.volume.VolumeService', '/VolumeService').switch_mute(False)"
# or
#    qdbus org.volume.VolumeService /VolumeService adjust_volume -10 False
#    qdbus org.volume.VolumeService /VolumeService switch_mute False


import gtk
import sys, os
import gobject
import os.path
import optparse
import ossaudiodev
import gobject
import dbus
import dbus.service
import dbus.mainloop.glib
import signal

appname = "adjvold"
# path must end with slash
icons_path = "/usr/share/icons/gnome/24x24/status/"

class VolumeService(dbus.service.Object):
	def __init__(self,bus,path):
		super(VolumeService,self).__init__(bus,path)
		self.pvol = Pvol()
		self.mixer = Mixer()
		self.mainloop = gobject.MainLoop()

	@dbus.service.method("org.volume.VolumeService",in_signature='', out_signature='i')
	def status(self):
		return self.mixer.get()
		
	@dbus.service.method("org.volume.VolumeService",in_signature='b', out_signature='')
	def switch_mute(self,quiet = True):
		self.mixer.switch_mute()
		if not quiet:
			self.pvol.set_percents_and_show(self.mixer.get())

	@dbus.service.method("org.volume.VolumeService",in_signature='ib', out_signature='')
	def adjust_volume(self,percents,quiet = True):
		if percents > 0:
			self.mixer.increase(percents)
		else:
			self.mixer.decrease(abs(percents))
		if not quiet:
			self.pvol.set_percents_and_show(self.mixer.get())
		
	@dbus.service.method("org.volume.VolumeService",in_signature='', out_signature='')
	def exit(self):
		del self.mixer
		self.mainloop.quit()

	def __handler__(self, signum, frame):
		self.exit()
		
	def setTimeout(self,timeout):
		signal.signal(signal.SIGALRM,self.__handler__)
		signal.alarm(timeout)
		
	def run(self):
		try: self.mainloop.run()
		except: exit(0)


class Mixer:
	def __init__(self,pcm = False):
		self.mixer = ossaudiodev.openmixer()
		self.channels = [['MASTER', ossaudiodev.SOUND_MIXER_VOLUME],
				['PCM', ossaudiodev.SOUND_MIXER_PCM]]
		self.channel = self.channels[0][1] if not pcm else self.channels[1][1]
		self.get = lambda: self.mixer.get(self.channel)[0]
		self.set = lambda percents: self.mixer.set(self.channel,(percents,percents))
		# pulseaudio default sink (required for unmute method)
		self.sink = os.popen('pactl info').read().split('Default Sink: ')[1].split('\n')[0]
		self.value_before_muted = 10
		
	def __del__(self):
		self.mixer.close()
		
	def increase(self,percents):
		if self.get() <= 0:
			self.unmute(percents)
		else:
			self.set(min(100,self.get() + percents))
		
	def decrease(self,percents):
		self.set(max(0,self.get() - percents))
		if self.get() <= 0:
			self.value_before_muted = 10
		
	def mute(self):
		self.value_before_muted = self.get()
		self.set(0)
	
	# seems like ossmixer is unable to unmute volume
	def unmute(self,value = None):
		os.system('pactl set-sink-mute ' + self.sink + ' 0')
		self.set(value if value != None else self.value_before_muted)
		
	def switch_mute(self):
		self.mute() if self.get() > 0 else self.unmute()


class Pvol:
	def __init__(self, wmname=appname):
		self.window = gtk.Window(gtk.WINDOW_POPUP)		
		self.window.set_title(wmname)
		self.window.set_border_width(1)
		self.window.set_default_size(180, -1)
		self.window.set_position(gtk.WIN_POS_CENTER)
		
		self.icons = {"high": None, "medium": None, "low": None, "muted": None}
		for name in self.icons:
			self.icons[name] = gtk.Image()
			self.icons[name].set_from_file(icons_path + "audio-volume-" + name + ".png")
			self.icons[name].show()

		self.icon = self.icons["high"]
		self.percents = 0

		self.progressbar = gtk.ProgressBar()
		self.progressbar.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)

		self.widgetbox = gtk.HBox()
		self.widgetbox.pack_end(self.icon)
		self.widgetbox.pack_end(self.progressbar)
		self.window.add(self.widgetbox)
		self.timer = -1
		self.window.show_all()
		self.window.set_visible(False)
		
	def set_percents(self,percents):
		self.percents = percents
		self.widgetbox.remove(self.icon)
		if percents <= 0:
			self.icon = self.icons["muted"]
		elif percents <= 33:
			self.icon = self.icons["low"]
		elif percents <= 66:
			self.icon = self.icons["medium"]
		else:
			self.icon = self.icons["high"]
		self.widgetbox.pack_end(self.icon)
		
	def set_percents_and_show(self,percents):
		self.set_percents(percents)	
		self.progressbar.set_fraction(float(percents) / 100)
		self.progressbar.set_text("%d%%" % percents)
		gobject.source_remove(self.timer)
		self.timer = gobject.timeout_add(2000, self.window.set_visible,False)
		if not self.window.get_visible():
			self.window.set_visible(True)

def main():
	dbus.set_default_main_loop(dbus.mainloop.glib.DBusGMainLoop())
	bus = dbus.SessionBus()
	name = dbus.service.BusName("org.volume.VolumeService",bus)
	VolumeServiceObject = VolumeService(bus, "/VolumeService")
	VolumeServiceObject.run()
	
	return 0


if __name__ == "__main__":
	main()

