#!/usr/local/bin/python

# Program: tr.new.sf.cgi
# Purpose: produces the HTML page for entering new tracking records
# User Requirements Satisfied by This Program:
#	see "Request Removal" requirements document under TR226
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface, with
#		parameters provided by a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: REMOTE_USER - WTS login name of the current user
#	Inputs: None
#	Outputs: An HTML page (a new tracking record short form screen) is sent
#		to stdout containing two tables of information to be filled in
#		for the new tracking record.  The top table includes who is
#		filling out the form, a box where he/she may choose a routing
#		category for the tracking record, and the title for the tracking
#		record.  In the lower table are Priority, Needs Attention By,
#		Size, and Project Definition.  All of these may be edited by the
#		user.  A Save button will save the user's entries for the
#		tracking record.  A Reset button will restore the default
#		entries for each field.  A WTS Home button would take the user
#		to the WTS Home Page.
#	Exit Codes: none
#	Other System Requirements: none
# Assumes: nothing
# Implementation:
#	As with all WTS CGI scripts, the main code for this one is wrapped in a
#	try..except statement.  This ensures that we can present an Exception
#	Screen for the user rather than having a hard crash.  (Both are
#	undesirable and should not happen under normal operating circumstances.)

import os
import sys
import Configuration
import screenlib	# provides access to tracking record information and a
			# means of manipulating tracking record data
import TrackRec		# provides a means of generating the HTML screen

try:
	tr = TrackRec.TrackRec ()	# init a new tracking record

	doc = screenlib.TrackRec_ShortForm_Screen ()	# create screen
	doc.setup (tr)					# fill screen w/ data
	doc.write ()					# write out the screen

except:
	screenlib.gen_Exception_Screen ('tr.new.sf.cgi')
