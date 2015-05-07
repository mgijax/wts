#!/usr/local/bin/python

# Program: tr.edit.cgi
# Purpose: presents an HTML form by which the user may edit information for a
#	specified tracking record.
# User Requirements Satisfied by This Program:
#	see original WTS User Requirements Document, functional requirements
#	10.1-10.5
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface,
#		with parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: none
#	Inputs: a single field (TrackRec, a string) which contains the integer
#		portion of the TR # of the tracking record to edit.
#	Outputs: An HTML page (a tracking record edit screen) is sent to
#		stdout, containing two tables of info for the specified
#		tracking record (TrackRec).  The top table includes TR #, the
#		current date and time, and the tracking record's title.  The
#		lower table contains the other small data fields:  Area, Type,
#		Staff, etc.  Below the lower table are the three large text
#		fields (Project Definition, Progress Notes).  All of these may
#		be edited by the user.  A Save button would save the state of
#		the tracking record, as edited.  A Cancel button would abort the
#		editing process and go back to the detail screen for that
#		tracking record.  Locks the tracking record, thus updating the
#		WTS_TrackRec table in the database.
#	Exit Codes: none
#	Other System Requirements: none
# Assumes:
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
	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# put it in a dictionary

	# get the number of the tracking record we need to edit (specified in
	# the 'TrackRec' field).

	tr_num = string.atoi (string.strip (dict ['TrackRec']))

	tr = TrackRec.TrackRec (tr_num)		# load the tracking record with
						# the specified number.

	if dict.has_key('unlock'):
		tr.unlock()

	# Now try to lock that tracking record.  If an exception is raised,
	# then we know that it has already been locked.  The string returned
	# with the exception (the exc_value) specifies who locked it and when.

	try:
		tr.lock ()				# lock tracking record
		doc = screenlib.TrackRec_Edit_Screen ()	# create the screen
		doc.setup (tr)				# fill in the screen
		doc.write ()				# write it out

	except TrackRec.alreadyLocked:
		screenlib.gen_Unlock_Screen (
			Configuration.config['PREFIX'] + \
			': Cannot Lock Tracking Record',
			tr_num, sys.exc_value, 1)
except:
	screenlib.gen_Exception_Screen ('tr.edit.cgi')
