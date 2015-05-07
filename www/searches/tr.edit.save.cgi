#!/usr/local/bin/python

# Program: tr.edit.save.cgi
# Purpose: accept, parse, and save information from a web-edited session on an
#	existing tracking record.
# User Requirements Satisfied by This Program:
#	see original WTS User Requirements Document, functional requirements
#	10.6, 12
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface, with
#		parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: none
#	Inputs: All fields from a tracking record edit form which were filled
#		in.  (Blank fields are not submitted via a POST operation.)
#		These may include any of the following tracking record fields:
#			TR_Nr			Needs_Attention_By
#			Title			Requested_By
#			Area			Depends_On
#			Type			Directory
#			Priority		Staff
#			Status			Forwarding
#			Status_Date		Project_Definition
#			Status_Staff		Progress_Notes
#			Size
#		One optional field may also be included:
#			Create_Directory_Flag - if this is present, it indicates
#				that we should create a project directory for
#				this tracking record (by including an optional
#				parameter in the save() operation).
#		Note also that the function "FieldStorage_To_Dict()" converts
#		the underscores in these fieldnames to spaces.
#	Outputs: May generate an HTML screen with reports of various data
#		validation errors, if any occurred, and giving him/her the
#		choice of going back to fix them or of aborting the editing
#		process.  Or, if the data is successfully validated, it will be
#		saved to the database and an HTML screen will be generated with
#		Javascript telling the browser to return to the previous
#		(tracking record display) screen and popping up a box which
#		reminds the user to do a Reload to get the current information.
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
	# get input from the edit tracking record form (web), and
	# convert it to a regular dictionary.  (and remove the field
	# corresponding to the Save button.

	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# put it in a dictionary

	del dict ['Save']	# remove the submitted Save button, since it is
				# not part of the data for a tracking record.

	# First, we need to look for the optional "Create_Directory_Flag" field.
	# If it is there, we need to remember that it was, and we then need to
	# remove it from the input "dict" as it is not a standard tracking
	# record field.

	if dict.has_key ('Create Directory Flag'):
		createProjectDirectory = 1		# set boolean flag
		del dict ['Create Directory Flag']
	else:
		createProjectDirectory = 0		# unset boolean flag

	# next, let's use the contents of the forwarding field to load the
	# routing category information, and then remove the field from the
	# input "dict"

	category = Category.Category (dict ['Forwarding'])
	del dict ['Forwarding']

	# now, validate the entries that were made for the tracking record:

	try:
		# validate_TrackRec_Entry both verifies and cleans up dict,
		# returning a cleaned-up dictionary

		clean_dict = TrackRec.validate_TrackRec_Entry (dict)

		valid = 1	# note that the data is valid - it was
				# cleaned properly
	except TrackRec.error:
		valid = None	# an exception occurred while cleaning the
				# data - note that it is not valid.

		# When the exception occurred in validation, the list of errors
		# encountered was returned in exc_value as a string.  The
		# individual errors are separated by the standard
		# "error_separator" defined in the TrackRec module.  Use wtslib
		# to convert this to a list of individual error strings.

		error_list = wtslib.string_To_List (sys.exc_value,
			TrackRec.error_separator)

		# now, build a screen to notify the user of the errors that
		# occurred.  To do this, the setup method needs to know:
		#	the list of errors
		#	what CGI to call if the user clicks the Abort button
		#	what tracking record needs to be unlocked
		#	how many screens to go back if the user clicks Abort

		doc = screenlib.Error_Screen (
			title = Configuration.config['PREFIX'] + \
				': Errors occurred in Edit Tracking Record')
		doc.setup (error_list,
			abort_cgi = 'tr.bailout.cgi',
			tr_num = dict ['TR Nr'],
			back_count = 3 )
		doc.write ()		# write out the error notice screen

	# if the data was found to be valid, then we can go ahead and save it.

	if valid:
		# Get the tracking record number included in the data, then
		# load in the corresponding tracking record.

		tr_num = string.atoi (clean_dict ['TR Nr'])	# get TR number
		tr = TrackRec.TrackRec (tr_num)			# load the TR

		# since some values may have been made null, they would
		# not have come through with the info from the form.  (POST
		# submissions only include non-null fields)  So, to have these
		# be properly set, we need to reset everything to the base
		# defaults, and then fill in those we do know.  (if we erased a
		# Depends On field, for example, it doesn't come through with
		# a blank; it just doesn't come through.)

		tr.set_Defaults ()		# reset the tracking record to
						# the standard default values.
		tr.set_Values (clean_dict)	# set all the values that just
						# came in the submission.

		# now, we may need to make adjustments to the Area, Type, Staff,
		# and Status fields as a result of the chosen routing category

		if category.getStaff () != '':
			tr.addToCV ('Staff', category.getStaff ())
		if category.getType () is not None:
			tr.addToCV ('Type', category.getType ())
		if category.getArea () is not None:
			tr.addToCV ('Area', category.getArea ())
		if category.getStatus () is not None:
			tr.set_Values ( { 'Status' : category.getStatus () } )

		# The "save ()" and "unlock ()" methods will raise a
		# TrackRec.notLocked exception if the current user does not
		# have the tracking record locked.  If this happens, then we
		# should present a message explaining the problem and send the
		# user back to the Edit screen.

		successful_save = 1		# assume a successful save op

		try:
			# if we need to create a project directory, then the
			# save() method needs an optional parameter

			if createProjectDirectory == 1:
				tr.save (createProjectDirectory)
			else:
				tr.save ()
			tr.unlock ()		# then unlock it.

		except TrackRec.notLocked:
			successful_save = 0	# save operation failed
			screenlib.gen_Message_Screen (
				'Tracking Record Locking Error',
				'You have %s' % sys.exc_value)

		if successful_save == 1:
			# send e-mail to notify (as needed) of forwarding
			# of the TR

			msg = category.sendNotification (
				os.environ ['REMOTE_USER'], tr)

			# The save is complete, so go back to detail screen,
			# possibly giving the user notice of forwarding
			# completion...

			if category.getName () == "don't route":
				# no new routing.  just go from new screen to
				# edit screen to detail screen = back twice

				screenlib.gen_GoTo_Screen ('tr.detail.cgi?TR_Nr=%s' % tr_num)
			else:
				# we forwarded the TR, so we need to notify
				# the user that it was successfully routed

				screenlib.gen_Message_Screen (
					"TR Forwarded", msg, 2)
except:
	screenlib.gen_Exception_Screen ('tr.edit.save.cgi')
