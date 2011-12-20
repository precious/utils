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
			self.pvol.set_fraction(self.mixer.get())

	@dbus.service.method("org.volume.VolumeService",in_signature='ib', out_signature='')
	def adjust_volume(self,percents,quiet = True):
		if percents > 0:
			self.mixer.increase(percents)
		else:
			self.mixer.decrease(abs(percents))
		if not quiet:
			self.pvol.set_fraction(self.mixer.get())
		
	@dbus.service.method("org.volume.VolumeService",in_signature='', out_signature='')
	def Exit(self):
		del self.mixer
		mainloop.quit()

	def __handler__(self, signum, frame):
		self.Exit()
		
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
		
	def __del__(self):
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
		os.system('pactl set-sink-mute ' + self.sink + ' 0')
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
		
	def set_fraction(self,percents):
		self.progressbar.set_fraction(float(percents) / 100)
		self.progressbar.set_text("%d%%" % percents)
		gobject.source_remove(self.timer)
		self.timer = gobject.timeout_add(2000, self.window.set_visible,False)
		if not self.window.get_visible():
			self.window.set_visible(True)
			

def process_options(options,volume_service,usage):
	is_quiet = bool(options.quiet)
	if options.mute:
		volume_service.switch_mute(is_quiet)
	elif options.percent:
		volume_service.adjust_volume(int(options.percent),is_quiet)
	elif options.status:
		print volume_service.get()
	elif not options.daemon:
		print usage
		exit(1)


def main():
	prog_name = os.path.basename(sys.argv[0])
	usage = "%s [-s] [-m] [-c PERCENT] [-p] [-q] [-d]" % prog_name
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-s', '--status', action='store_true', dest='status', help='display current volume')
	parser.add_option('-m', '--mute', action='store_true', dest='mute', help='mute the main audio channel')
	parser.add_option('-c', '--change', type='int', dest='percent', help='increase or decrease volume by given percentage')
	parser.add_option('-p', '--pcm', action='store_true', dest='pcm', default=False, help='change PCM channel (default is MASTER)')
	parser.add_option('-q', '--quiet', action='store_true', dest='quiet', help='adjust volume without the progressbar')
	parser.add_option('-d', '--daemon', action='store_true', dest='daemon', help=('start %s dbus service as daemon' % prog_name))
	(option, args) = parser.parse_args()

	dbus.set_default_main_loop(dbus.mainloop.glib.DBusGMainLoop())
	bus = dbus.SessionBus()
	is_service = False
	try:
		VolumeServiceObject = bus.get_object("org.volume.VolumeService", "/VolumeService")
	except dbus.DBusException:
		is_service = True
		name = dbus.service.BusName("org.volume.VolumeService",bus)
		VolumeServiceObject = VolumeService(bus, "/VolumeService")
		# how many secons service should remain in memory
		if not option.daemon:
			VolumeServiceObject.setTimeout(60)
	process_options(option,VolumeServiceObject,usage)
	if is_service:	
		VolumeServiceObject.run()
	
	return 0


if __name__ == "__main__":
	main()

