#!/bin/bash

IFS=$'\n'
for f in `find -iregex '.*\.desktop'`; do
	# parse executable's name from desktop file
	name="`cat "$f" 2> /dev/null | grep -m1 "^Exec" | sed "s/^Exec=//gi" | grep -Po '^[^ ]+'`"
	# if executable's name contains " or ' -- then continue
	if [  ! "$name" -o `expr index "$name" "'"` -gt 0 -o  `expr index "$name" '"'` -gt 0 ] ; then
		continue
	else
		which "$name" > /dev/null 2>&1
		if [ $? -ne 0 ] ; then
			rm "$f"
			echo "$f -- broken desktop file has been deleted"
		fi
	fi
done
