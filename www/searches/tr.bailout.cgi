#!/usr/local/bin/python

# Program: tr.bailout.cgi
# Purpose: After cancelling an edit session (web-based) on an existing tracking
#	record, we need to somehow release the lock on that tracking record.
#	This cgi script unlocks the tracking record and then goes back a certain
#	number of screens in the user's browser's history list.
# User Requirements Satisfied by This Program:
#	see original WTS User Requirements Document, functional requirements
#	10.5-10.6
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface,
#		with parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: none
#	Inputs: two fields via a GET or POST submission:  TR_Nr (the integer
#		tracking record number to unlock; optional; default None) and
#		BackCount (the number of screens to go back).
#	Outputs: A blank HTML page is sent to stdout as a response to the
#		submission.  It contains Javascript code needed to immediately
#		go back a certain number of entries in the user's browser's
#		history list.  Unlocks the tracking record, thus updating the
#		WTS_TrackRec table in the database.
#	Exit Codes: none
#	Other System Requirements: none
# Assumes: If the TR_Nr field is specified, it identifies a valid tracking
#	record.
# Implementation:
#	As with all WTS CGI scripts, the main code for this one is wrapped in a
#	try..except statement.  This ensures that we can present an Exception
#	Screen for the user rather than having a hard crash.  (Both are
#	undesirable and should not happen under normal operating circumstances.)

import os
import sys
import cgi
import string
import Configuration
import wtslib		# provides auxiliary functions
import TrackRec		# provides access to tracking record information and a
			# means of manipulating tracking record data
import screenlib	# provides a means of generating the HTML screen

try:
	# get input values, and convert them to a regular dictionary.

	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# convert to dictionary

	# The number of screens to go back is a mandatory field named
	# BackCount.  Get its value, convert it to an integer, and put it in
	# back_ct.

	back_ct = string.atoi (string.strip (dict ['BackCount'] ) )

	# if the optional tracking record number (to unlock) was specified,
	# then get it and convert it to an integer in tr_num.  Then load that
	# tracking record and unlock it.

	if 'TR Nr' in dict.keys ():
		tr_num = string.atoi (string.strip (dict ['TR Nr']) )
		tr = TrackRec.TrackRec (tr_num)		# load the tracking rec

		# We need to unlock the specified tracking record.  The
		# TrackRec.notLocked exception is raised if the current user
		# does not have it locked, in which case we can just ignore
		# the exception and proceed.

		try:
			tr.unlock ()		# unlock it
		except TrackRec.notLocked:
			pass			# if we don't have it locked,
						# then we don't need to free it
		
	# Lastly, go back the required number of screens

	screenlib.gen_GoBack_Screen (back_ct)
except:
	screenlib.gen_Exception_Screen ('tr.bailout.cgi')
