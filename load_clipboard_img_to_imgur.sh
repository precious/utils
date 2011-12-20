#!/bin/bash

SCRIPTS_DIR="/home/precious/programming/useful_scripts"
IMG_PATH="/home/precious/Screenshots"
FILENAME=`$SCRIPTS_DIR/save_clipboard_image.py "$IMG_PATH"`
if [ $? == 0 ] ; then
	$SCRIPTS_DIR/load_img_to_imgur.sh $FILENAME
else
	notify-send "There is no valid image in the clipboard"
fi

