#!/usr/local/bin/python

# Program: tr.status.grid.cgi
# Purpose: to parse input fields and use them to query the database and return
#	a Status Grid screen
# User Requirements Satisfied by This Program:
#	see TR 659
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface, with
#		parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: none
#	Inputs: Requires two fields be filled in:
#		RowType = 'Area' or 'Type'
#		DateRange = string, specifying range of dates
#	Outputs: May generate an HTML screen with reports of various data
#		validation errors, if any occurred, and giving him/her the
#		choice of going back to fix them or of aborting the querying
#		process.  Or, if the data is successfully validated, it will be
#		used to generate and run queries to get selected information
#		about tracking records from the database.  This info is then
#		use to produce an HTML screen for the desired Status grid.
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
import cgi
import string
import Configuration
import wtslib		# provides auxiliary functions
import TrackRec		# provides access to tracking record information and a
			# means of manipulating tracking record data
import screenlib	# provides a means of generating the HTML screens

try:
	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# convert to dictionary

	# Check the values in the input.  Both fields must be specified, and
	# valid.  If not, give the user a chance to go back to correct them.

	errors = []
	if not dict.has_key ('DateRange'):
		errors.append ('A date range must be specified.')
	if not dict.has_key ('RowType'):
		errors.append ('You must select a type of analysis.')
	elif dict ['RowType'] not in [ 'Area', 'Type' ]:
		errors.append ('Valid analysis options are Area and Type.')

	if len (errors) == 0:
		try:
			tbl = TrackRec.getStatusTable (dict ['RowType'],
				dict ['DateRange'])
			doc = screenlib.Status_Grid_Screen ()
			doc.setup (dict ['RowType'], dict ['DateRange'], tbl)
		except TrackRec.error:
			errors = wtslib.string_To_List (sys.exc_value,
				TrackRec.error_separator)
	if len(errors) > 0:
		# bring up the error notification screen to give the user the
		# full info about what errors were discovered.

		doc = screenlib.Error_Screen ()	# create the error screen
		doc.setup (errors)		# setup it up w/ list of errors
	doc.write ()
except:
	screenlib.gen_Exception_Screen ('tr.query.results.cgi')
