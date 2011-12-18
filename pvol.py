#!/usr/bin/env python

# pvol -- Commandline audio volume utility
#		with an optional GTK progressbar
#		and which is able to remain in memory some time as dbus service
#		(to prevent multiple gtk popup window creation) 
# Copyright (C) 2009 Adrian C. <anrxc_sysphere_org>
#		2011 Seva K. <vs_kulaga_gmail_com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


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

appname = "Pvol"
appicon = os.path.expanduser("/usr/share/icons/gnome/22x22/status/audio-volume-high.png")


class NotifyServer(dbus.service.Object):
	def __init__(self,bus,obj):
		super(NotifyServer,self).__init__(bus,obj)
		self.pvol = Pvol()
		gtk.main()
	@dbus.service.method("org.volume.NotifyServer",in_signature='i', out_signature='b')
	def setPercents(self, percents):
		self.pvol.setFraction(percents)
		return True
	
	@dbus.service.method("org.volume.NotifyServer",in_signature='', out_signature='')
	def Exit(self):
		gtk.main_quit()
		mainloop.quit()

	def __handler__(signum, frame):
		self.Exit()
		
	def setTimeout(self,timeout):
		signal.signal(signal.SIGALRM,self.__handler__)
		signal.alarm(timeout)


class Mixer:
	def __enter__(self,pcm = False):
		self.mixer = ossaudiodev.openmixer()
		self.channels = [['MASTER', ossaudiodev.SOUND_MIXER_VOLUME],
				['PCM', ossaudiodev.SOUND_MIXER_PCM]]
		self.channel = self.channels[0][1] if not pcm else self.channels[1][1]
		self.get = lambda: self.mixer.get(self.channel)[0]
		self.set = lambda percents: self.mixer.set(self.channel,(percents,percents))
		return self
		
	def __exit__(self, type, value, traceback):
		self.mixer.close()
		
	def increase(self,percents):
		if self.get() <= 0:
			self.unmute(percents)
		else:
			self.set(min(100,self.get() + percents))
		
	def decrease(self,percents):
		self.set(max(0,self.get() - percents))
		
	def mute(self):
		self.set(0)
	
	# seems like ossmixer is unable to unmute volume
	def unmute(self,value = 10):
		sink = os.popen('pactl info').read().split('Default Sink: ')[1].split('\n')[0]
		os.system('pactl set-sink-mute ' + sink + ' 0')
		self.set(value)
		
	def switch_mute(self):
		self.mute() if self.get() > 0 else self.unmute()


class Pvol:
	def __init__(self, wmname=appname):
		self.window = gtk.Window(gtk.WINDOW_POPUP)		
		self.window.set_title(wmname)
		self.window.set_border_width(1)
		self.window.set_default_size(180, -1)
		self.window.set_position(gtk.WIN_POS_CENTER)

		self.icon = gtk.Image()
		self.icon.set_from_file(appicon)
		self.icon.show()

		self.progressbar = gtk.ProgressBar()
		self.progressbar.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)

		self.widgetbox = gtk.HBox()
		self.widgetbox.pack_start(self.icon)
		self.widgetbox.pack_start(self.progressbar)
		self.window.add(self.widgetbox)
		self.timer = -1
		self.window.show_all()
		self.window.set_visible(False)
		
	def setFraction(self,percents):
		self.progressbar.set_fraction(float(percents) / 100)
		self.progressbar.set_text("%d%%" % percents)
		gobject.source_remove(self.timer)
		self.timer = gobject.timeout_add(2000, self.window.set_visible,False)
		if not self.window.get_visible():
			self.window.set_visible(True)

def main():
	usage = "%s [-s] [-m] [-c PERCENT] [-p] [-q]" % os.path.basename(sys.argv[0])
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-s', '--status', action='store_true', dest='status', help='display current volume')
	parser.add_option('-m', '--mute', action='store_true', dest='mute', help='mute the main audio channel')
	parser.add_option('-c', '--change', type='int', dest='percent', help='increase or decrease volume by given percentage')
	parser.add_option('-p', '--pcm', action='store_true', dest='pcm', default=False, help='change PCM channel (default is MASTER)')
	parser.add_option('-q', '--quiet', action='store_true', dest='quiet', help='adjust volume without the progressbar')
	(option, args) = parser.parse_args()

	with Mixer() as mixer:
		if option.mute:
			mixer.switch_mute()
		elif option.percent:
			value = int(option.percent)
			mixer.increase(value) if value > 0 else mixer.decrease(abs(value))
		elif option.status:
			print(mixer.get())
		else:
			print usage
			exit(1)
		percents = mixer.get()

	if option.quiet:
		return 0

	dbus.set_default_main_loop(dbus.mainloop.glib.DBusGMainLoop())
	bus = dbus.SessionBus()
	try:
		NotifyServerObject = bus.get_object("org.volume.NotifyServer", "/NotifyServer")
		NotifyServerObject.setPercents(percents,dbus_interface = "org.volume.NotifyServer")
	except dbus.DBusException:
		name = dbus.service.BusName("org.volume.NotifyServer",bus)
		object = NotifyServer(bus, "/NotifyServer")
		# how many secons service should remain in memory
		object.setTimeout(60)
		object.setPercents(percents)

		mainloop = gobject.MainLoop()
		try: mainloop.run()
		except: exit(0)
	
	return 0


if __name__ == "__main__":
	main()

