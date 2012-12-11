#!/bin/bash
#
# Original by Sirupsen @ http://sirupsen.dk# Edited end re-edited by 3demax
# Description: Very simple script to make you
# select a region of your screen, which will be captured, and
# then uploaded. The URL will then be injected into your clipboard.
#
# Dependencies:
#
# Compiz
#
# Xclip
# Comment: Xclip injects the direct url into your clipboard.
#
# libnotify*
# Comment: Will notify you whenever the direct URL is in the clipboard

filename=$1

# export http_proxy=http://localhost:9045

function uploadImage {
  #curl -s -F "image=@$1" -F "key=6af857bfde70d28a6df70be425e453bc" http://imgur.com/api/upload.xml | grep -Po "(?<=<original_image>).*(?=</original_image>)"
  curl -s -F "image=@$1" -F "key=6af857bfde70d28a6df70be425e453bc" 'http://api.imgur.com/2/upload.json' | python -c 'import sys, json; print json.loads(sys.stdin.read())["upload"]["links"]["original"]'
}

DIR=`dirname $filename`
DATE=`date +"%F_%R:%S"`
cd $DIR
if [ $? == 0 ]
then
        link=`uploadImage "$filename"`
	echo $link
        echo "$link" | xclip -selection c
        echo "$DATE $filename $link" >> "$DIR/links.txt"
        notify-send "Image upload done" "$filename<br>$link"
else
        notify-send "Image upload failed" "Exitcode $?"
fi
