#!/usr/local/bin/python

# Program: tr.new.save.cgi
# Purpose: accept, parse, and save information from a web-entry session on a
#	new tracking record.
# User Requirements Satisfied by This Program:
#	see original WTS User Requirements Document, functional requirements
#	4.2, 9.6, 12
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface, with
#		parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: none
#	Inputs: All fields from a new tracking record form which were filled
#		in.  (Blank fields are not submitted via a POST operation.)
#		These may include any of the following tracking record fields:
#			Size			Needs_Attention_By
#			Title			Requested_By
#			Area			Depends_On
#			Type			Directory
#			Priority		Staff
#			Status			Routing
#			Status_Date		Project Definition
#			Status_Staff		Progress_Notes
#		And one optional one, which is not a tracking record field:
#			Create_Directory_Flag - if this field is present, it
#				indicates that we should create a project
#				directory for this tracking record.
#		It should also be noted that the FieldStorage_To_Dict() function
#		converts underscores in the fieldnames to be spaces.
#	Outputs: May generate an HTML screen with reports of various data
#		validation errors, if any occurred, and giving him/her the
#		choice of going back to fix them or of aborting the editing
#		process.  Or, if the data is successfully validated, it will be
#		saved to the database and an HTML screen will be generated to
#		notify the user of the number of the new tracking record.
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
import screenlib	# provides a means of generating the HTML screen
import Category		# allows access to routing categories

try:
	# get input from the new tracking record form (web), and
	# convert it to a regular dictionary.  (and remove the field
	# corresponding to the Save button)

	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# convert to dictionary

	del dict ['Save']	# The Save button is not part of the tracking
				# record's data, but it does come in as an
				# input field.  So, remove it before we try to
				# save the data.

	# first, let's see if we need to create a project directory for this
	# tracking record.  If so, remember that and remove the field from the
	# input "dict" (because it is not a standard tracking record field).

	if dict.has_key ('Create Directory Flag'):
		createProjectDirectory = 1		# set boolean flag
		del dict ['Create Directory Flag']
	else:
		createProjectDirectory = 0		# unset boolean flag

	# next, let's remember use contents of the routing field to load the
	# routing category information, and then remove the field from the
	# input "dict"

	category = Category.Category (dict ['Routing'])
	del dict ['Routing']

	# Now, validate the entries that were made.  If the validation process
	# discovers an error, an exception is raised.

	try:
		clean_dict = TrackRec.validate_TrackRec_Entry (dict)
		valid = 1	# no errors were found - data is valid
	except TrackRec.error:
		valid = None	# errors were found - data is invalid

		# At least one error was found in the data.  The errors are
		# returned as a comma-space separated string in exc_value when
		# the exception is raised.  So, we need to generate an error
		# screen which notifies the user of the errors and then gives
		# him/her the option of going back to fix them or just aborting.

		# create the error screen

		doc = screenlib.Error_Screen ( \
			title = Configuration.config['PREFIX'] + \
				': Errors occurred in ' + \
				'New Tracking Record Entry')

		# To setup the error screen, we need to give it a list of
		# strings (one for each error which occurred)

		doc.setup (wtslib.string_To_List (sys.exc_value,
				TrackRec.error_separator))
		doc.write ()					# write screen

	if valid:	
		# create a new tracking record, alter it,
		# save it, and remember its number.

		tr = TrackRec.TrackRec ()	# init a new tracking record
		tr.set_Values (clean_dict)	# give it the input values

		# we may need to make adjustments to the Area, Type, Staff, and
		# Status fields as a result of the chosen routing category

		if category.getStaff () != '':
			tr.addToCV ('Staff', category.getStaff ())
		if category.getType () is not None:
			tr.addToCV ('Type', category.getType ())
		if category.getArea () is not None:
			tr.addToCV ('Area', category.getArea ())
		if category.getStatus () is not None:
			tr.set_Values ( { 'Status' : category.getStatus () } )

		# Since this is a new tracking record, the "save ()" method
		# does not check to see if it is locked.  Thus, we don't need
		# to worry about catching the TrackRec.notLocked exception as
		# we do in the other CGI scripts.

		tr.save (createProjectDirectory)

		# send an e-mail notification for the routing category, and
		# remember the message ("msg") that was sent

		msg = category.sendNotification (os.environ ['REMOTE_USER'], tr,
			1)

		# We are now ready to create a notification screen for the
		# user which will tell him/her the number of the newly saved
		# tracking record.

		doc = screenlib.TR_Notification_Screen ()	# create screen

		doc.setup (tr.num (), msg)	# set it up using the TR number
						# and the routing message
		doc.write ()			# write out the screen
except:
	screenlib.gen_Exception_Screen ('tr.new.save.cgi')
