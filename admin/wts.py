#!/usr/local/bin/python

# Program: wts.py
# Purpose: Implements the command-line interface for WTS, currently including:
#	creating, displaying, editing, and unlocking tracking records.
# User Requirements Satisfied by This Program:
#	see WTS User Requirements Document, functional requirement 13
# System Requirements Satisfied by This Program:
#	Usage: see definition of USAGE variable below
#	Uses: Python 1.4, WTS module: TrackRec, Template_File
#	Envvars: REMOTE_USER - set to user's login name (for other WTS modules)
#		 LOGNAME - used to set REMOTE_USER (contains Unix login name)
#		 WTS_EDITOR - can be set to specify the command line for the
#			editor to be used when editing tracking records
#		 EDITOR - if WTS_EDITOR is not set, we look to this semi-
#			standard environment variable for the user's preferred
#			editor
#	Inputs: up to two command-line parameters -- the first identifies the
#		type of operation to perform (-display, -edit, -unlock, -new)
#		and the second provides the tracking record number on which
#		to operate (for the first three of those operations).
#	Outputs: Note that all interaction with the user is handled through
#		stdin / stdout.  The various outputs differ depending on the
#		operation...
#		For -display operations, prints the contents of the specified
#		tracking record to stdout.
#		For -edit and -new operations, the script creates a text file
#		which contains the data for a tracking record.  It then fires
#		up a text editor and loads in that text file.  Once the user
#		has existed the editor (possibly after editing and saving the
#		text file), the script asks if it should import the file and
#		save the revised tracking record to WTS.
#		For the -unlock option, we just print a message confirming that
#		the record was unlocked.
#	Exit Codes: none
#	Other System Requirements: none
# Assumes: nothing
# Implementation:
#	Modules:
#		TrackRec - provides means of retrieving, saving, and validating
#			tracking records, along with a list of which fields
#			should not be edited.
#		Template_File - provides a mechanism for saving a dictionary
#			neatly to an external file, then importing from an
#			edited external file back to a dictionary.  This is
#			the mechanism for converting tracking records to their
#			text file representations.

USAGE = \
'''
	wts has several command line formats:
		wts --addNote <tr #>
		wts --addNoteFromFile <tr #> <full path to file>
		wts --batchInput <full path to file>
		wts --dir <tr #>
		wts --display <tr #>
		wts --edit <tr #>
		wts --fixTC <tr #>
		wts --getField <tr #> <fieldname>
		wts --locks
		wts --new
		wts --newMinimal <Title> <Status>
		wts --plainTree <tr #>
		wts --queryTitle <query string>
		wts --routing
		wts --setField <tr #> <fieldname> <field value>
		wts --tree <tr #>
		wts --unlock <tr #>

	For working with the MASS-T, you can substitute masst for wts in each
	of the above examples.

	For an explanation of these options, see the FAQ page in the WTS
	web interface.
'''

import os
import sys
import string
import tempfile
import time

# CGI programs set the REMOTE_USER environment variable automatically.  Since
# this is a shell program, we need to define it manually here.  (Other WTS
# modules expect it to be set with the login name of the current user, so we
# need to make sure that it is set here.)

os.environ ['REMOTE_USER'] = os.environ ['LOGNAME']	# LOGNAME is a standard
							# environment variable
							# which stores the name
							# of the unix user.
import Configuration
import batchInput
import wtslib
import TrackRec
import Template_File
import Controlled_Vocab
import Category

cmdError = 'WTS command-line error'

###--- Exit Codes ---###

ERR_UNLOCK = -1		# failed to unlock a TR
ERR_DATABASE = -2	# error in querying / contacting the database
ERR_READFILE = -3	# error in reading a file from the file system
ERR_TR = -4		# error occurred while using the TrackRec module
ERR_LOCKED = -5		# TR was already locked
ERR_PARSING = -6	# error in parsing the TR Number specification
ERR_MISSING = -7	# specified TR is not in the database
ERR_CMDLINE = -8	# miscellaneous error detected by the cmd line int.

# -- supporting functions --

def error (message):
	if type(message) == type(''):
		message = [ message ]
	sys.stderr.write (string.join (message, '\n') + '\n')
	return

def get_initial_char (
	valid_chars	# a non-empty string containing characters which are to
			# be considered valid return values for this function
	):
	# Purpose: present a prompt, read a line of input, and return the
	#	first character if it is in valid_chars.  Otherwise, present
	#	an error message and repeat the prompt, read, return cycle.
	# Returns: returns the user's choice of the characters in valid_chars
	# Assumes: valid_chars is non-empty (otherwise we're in an infinite
	#	loop)
	# Effects: reads a line of text and returns the initial character, in
	#	uppercase form, if it is in valid_Chars.  If it is not in
	#	valid_chars, we keep prompting and reading a new line of text
	#	until the user enteres a character that is in valid_chars.
	# Throws: nothing
	# Example: Typical usage would probably look something like...
	#	print "Do you want to import the tracking record? (Y/N)"
	#	answer = get_initial_char ('YN')

	valid_upper = string.upper (valid_chars)	# uppercase set of
							# valid characters

	# present a '>' prompt.  read a line of input.  strip off leading and
	# trailing blanks.  get the first character.  make it uppercase, and
	# put it in response.

	response = string.upper (string.strip (raw_input ('>'))[0])

	# as long as the response is not valid, present an error message and
	# get a new line of input (in the same manner as we do above).

	while response not in valid_upper:
		print 'Please respond with one of the following: ', valid_chars
		response = string.upper (string.strip (raw_input ('>'))[0])

	return response		# at this point, response is one of the valid
				# characters, so return it.

def get_Category (
	message		# string; message to be displayed at the menu's top
	):
	# Purpose: display a menu of routing categories from which the user
	#	will choose one
	# Returns: the Category object corresponding to the name chosen
	# Assumes: nothing
	# Effects: sends a menu to stdout, reads from stdin
	# Throws: 1. raises an IndexError if there are no routing categories,
	#	2. propagates wtslib.sqlError if there are problems in getting
	#	the categories from the database

	# get info about the routing Categories

	category_list = Controlled_Vocab.cv ['CV_WTS_Category'].ordered_names ()
	num_categories = len (category_list)

	print message					# print the menu
	for i in range (0, num_categories):
		print "%d. %s" % (i, category_list [i])
	print
	print "Please enter the number of your choice:"

	num = -1					# chosen menu option
	valid_entry = 0					# no valid entry yet

	while not valid_entry:

		# each time through the loop, get a new input and try to
		# convert it to an integer.  Then, test to see if it one of the
		# menu options.  If so, it is valid and we can exit the loop.

		response = string.strip (raw_input ('>'))
		try:
			num = string.atoi (response)
			if (num >= 0) and (num < num_categories):
				valid_entry = 1
		except ValueError:
			pass		# could not convert "response" to int
		if not valid_entry:
			print "Please enter a number from 0 to %d" % \
				(num_categories - 1)

	return Category.Category (category_list [num])


def display_Tracking_Record (
	tr				# a TrackRec object to print
	):
	# Purpose: print a plain text representation of tr to stdout
	# Returns: nothing
	# Assumes: nothing
	# Effects: sends a plain text representation of tr to stdout
	# Throws: nothing

	dict = tr.dict ()		# get a dictionary of fieldnames &
					# values for the tracking record.
	fields = tr.all_Attributes ()	# get a list of the fieldnames in the
					# order in which they should be printed.
	dict_keys = dict.keys ()	# get the fieldnames included in this
					# particular tracking record.

	# go through the fields and print each one

	for key in fields:

		# if this key is defined for this tracking record, then get its
		# value.  Otherwise, just use 'None' to indicate that it has no
		# current value.

		if key in dict_keys:
			value = str (dict [ key ])
		else:
			value = 'None'

		# now, if the value is under 55 characters, we can print both
		# the fieldname (left justified in 20 columns) and the value on
		# the same line.

		if len (value) < 55:
			print string.ljust (key, 20), value
		else:
			print key	# otherwise, print the key on one line
			print value	# and the value on the next.
		

def unlock_Tracking_Record (
	tr				# the tracking record to be unlocked
	):
	# Purpose: unlock tr and print a message confirming that it was
	#	successfully unlocked.  This is only meant to remove a lock that
	#	has persisted in error, like if someone's browser crashed or if
	#	they backed out of editing a tracking record instead of
	#	cancelling the edit operation.
	# Returns: nothing
	# Assumes: tr is a locked TrackRec object
	# Effects: see Purpose.
	# Throws: nothing

	try:
		tr.unlock (1)	# set the override flag so that we will unlock
				# the tracking record regardless of who has it
				# locked.  (This is special for the command-
				# line interface.)
		print 'Unlock successful'

	except wtslib.sqlError:
		# This should only occur in case of a database / server error.

		error ( [ 'An exception occurred in trying to unlock the ',
			'tracking record.  The following message was ',
			'returned:',
			sys.exc_value ] )
		sys.exit (ERR_UNLOCK)
	return


# ----- BEGIN: supplemental functions for editing and creating tracking records

def genTemplateFile (
	tr,		# TrackRec object used to build the template file
	filename	# name of the file to generate
	):
	# Purpose: writes out a Template File to "filename" containing the
	#	data in tracking record object "tr"
	# Returns: a TemplateFile object
	# Assumes: user has permission to write "filename" to the file system
	# Effects: see Purpose
	# Throws: nothing

	# get a dictionary of fields to put in the template file, and remove
	# those that should not show up in the file to edit...

	dict = tr.dict ()	# get dictionary representation of the
				# fieldnames and values in the tracking record

	# TrackRec.NO_TEXT_EDIT is a list of names for fields which should not
	# show up in an external file to be edited.  We can just omit them from
	# dict so that they do not appear in the file.

	for key in TrackRec.NO_TEXT_EDIT:
		if dict.has_key (key):		# if that key is in dict...
			del dict [key]		# remove it and its value

	# ensure that all fields will have a value or the string "None",
	# rather than just a blank space...  (the user needs to see what he
	# or she is editing, and blanks don't show up very well)

	for key in dict.keys():
		if (dict [key] is None) or (dict [key] == ''):
			dict [key] = 'None'

	# create the template file by specifying the name of the file to
	# create, the fieldnames and values, and a list specifying how the
	# fields should be ordered.

	tf = Template_File.Template_File (filename, dict, tr.all_Attributes () )

	tf.save ()	# save the template file to the current directory
	return tf	# and return it


def getEditor ():
	# Purpose: return the command-line for the user's preferred editor
	# Returns: a string containing the command line for the user's editor
	# Assumes: nothing
	# Effects: Checks the environment to see if the user defined his/her
	#	preferred WTS editor in WTS_EDITOR.  If not, we then check the
	#	EDITOR environment variable.  If neither is defined, we use
	#	'vi' as a default.
	# Throws: nothing

	if os.environ.has_key ('WTS_EDITOR'):		# use WTS_EDITOR if
		return os.environ ['WTS_EDITOR']	# specified.
	elif os.environ.has_key ('EDITOR'):		# otherwise, use the
		return os.environ ['EDITOR']		# standard EDITOR
	else:						# setting.  otherwise,
		return 'vi'				# just use vi.

	
def editAndImportTemplate (
	tf		# the TemplateFile object to edit and import
	):
	# Purpose: pop open the user's editor, let him/her edit the data in
	#	"tf", then ask if we should read it back in.
	# Returns: a tuple with:  (boolean flag for whether to save the data,
	#	a dictionary of field and values to be saved.
	# Assumes: nothing
	# Effects: Once the user has exited his/her editor, he/she may choose
	#	to import the data or not.  This choice will be returned in the
	#	boolean flag.  If yes, we'll also return a dictionary with the
	#	new values.  If not, we'll return an empty dictionary.
	# Throws: nothing

	# fire up the editor using the filename as a parameter, and wait for
	# the user to exit the editor.

	os.system (getEditor () + ' ' + tf.getFilename())

	# ask the user if he/she wants to import the new info to the database

	print 'Would you like WTS to parse the file '
	print 'and update the database with the new '
	print 'information?  (Y/N)'

	# do we need to import the data?

	if get_initial_char ('YN') == 'Y':
		tf.load ()		# load & parse the file, then
		entries = tf.dict ()	# get the dictionary from file
		return (1, entries)
	else:
		return (0, {})		# no save, no need to load data


def validateAndSave (
	new_values,		# dictionary of new fields and values for tr
	tr			# the tracking record to be updated & saved
	):
	# Purpose: validate the entries in "new_values", then put them in "tr"
	#	and save them, handle routing of new tracking records.
	# Returns: the tracking record number of "tr"
	# Assumes: nothing
	# Effects: validates the entries in "new_values", then puts the values
	#	in "tr" and saves them.  sends e-mail to a routing category if
	#	this is a new tracking record.  (involves writing a menu of
	#	routing categories to stdout and reading from stdin)
	# Throws: propagates - 1. IndexError if this is an existing tracking
	#	record and it cannot be found in the database, 2. TrackRec.error
	#	if an error occurs in data validation, 3. wtslib.sqlError if a
	#	problem occurs executing any of the SQL statements,
	#	4. TrackRec.notLocked if the current user does not have "tr"
	#	locked.

	# validate and clean up the entries in the "new_values"

	clean_dict = TrackRec.validate_TrackRec_Entry (new_values)

	# set the new values in "tr"

	tr.set_Values (clean_dict)

	# if this is a new tracking record (indicated by having no number),
	# then we need to route it

	if tr.num () == 'None':

		# let the user pick a routing category, then:
		#	ensure that all staff members for that category are
		#		included in the tracking record's Staff field
		#	save the tracking record
		#	send an e-mail notification to those in the category

		category = get_Category ('Route this tracking record to:')
		tr.addToCV ("Staff", category.getStaff ())
		tr.save ()				# save updated record

		msg = category.sendNotification (os.environ ['REMOTE_USER'], tr)
		if len (msg) > 0:
			print "Routing Response:\t%s" % msg
			print

	# otherwise, this is an existing tracking record (which does not need
	# to be routed), so just save it.

	else:
		tr.save ()			# save the updated record
	return


def createMinimalTR (
	title,		# string; value for the Title field
	status		# string; value for the Status field
	):
	# Purpose: create a new TR, validate the 'title' and 'status' entries,
	#	then save the TR
	# Returns: string; the TR number which was assigned to the new TR
	# Assumes: nothing
	# Effects: updates the database by adding a new TR
	# Throws: propagates 'TrackRec.error' if an error occurs in data
	#	validation; raises 'cmdError' if a problem occurs when saving
	#	the new TR

	# validate and clean up the parameter values

	areas = Controlled_Vocab.cv['CV_WTS_Area']
	types = Controlled_Vocab.cv['CV_WTS_Type']
	priorities = Controlled_Vocab.cv['CV_WTS_Priority']
	sizes = Controlled_Vocab.cv['CV_WTS_Size']

	new_values = {
		'Title' : title,
		'Status' : status,
		'Requested By' : os.environ['REMOTE_USER'],
		'Area' : areas.keyToName (areas.default_key()),
		'Type' : types.keyToName (types.default_key()),
		'Priority' : priorities.keyToName (priorities.default_key()),
		'Size' : sizes.keyToName (sizes.default_key()),
		}
	clean_dict = TrackRec.validate_TrackRec_Entry (new_values)

	# set the new values in a new "tr"

	tr = TrackRec.TrackRec()
	tr.set_Values (clean_dict)

	try:
		tr.save ()
	except wtslib.sqlError:
		raise cmdError, 'Could not save new TR'
	return tr.num()


# ----- END: supplemental functions for editing and creating tracking records


def edit_Tracking_Record (
	tr			# the TrackRec object for the tracking record
				# to be edited.
	):
	# Purpose: provides a means for editing existing tracking records via
	#	the command line, and then saving the information if desired.
	# Returns: nothing
	# Assumes: The current user has write permission for the current
	#	directory.
	# Effects: Creates a text file with the data from tr.  Starts up a
	#	text editor and loads in the text file for the user to edit.
	#	Once the user has exited the editor, prompt to ask if changes
	#	in the text file should be imported to WTS or not.  Then,
	#	import if it was desired.  Since we are editing an existing
	#	tracking record, make sure we lock the record before editing
	#	and unlock it when finished.
	# Throws: propagates TrackRec.alreadyLocked if this tracking record
	#	has already been locked by someone else

	tr.lock ()	# Try to lock the tracking record.  If this fails, a
			# TrackRec.alreadyLocked exception will be propagated.

	# Use the tempfile module to ensure that our filename will be unique in
	# the current directory.  (We don't want to overwrite any existing
	# files.)

	tempfile.tempdir = "."				# work in current dir
	tempfile.template = "wts.tr%s." % tr.num ()	# filename template
	filename = tempfile.mktemp ()			# get a unique filename
	
	tf = genTemplateFile (tr, filename)	# get a Template_File object

	# keep going until we have reached a definite finish to the editing
	# process...  (either it imported successfully, or the user declined
	# to import it)

	finished = 0		# not finished yet -- we've just started

	while not finished:
		saveFlag, entries = editAndImportTemplate (tf)

		if not saveFlag:
			finished = 1	# don't try to save, just skip it
		else:
			try:
				validateAndSave (entries, tr)
				finished = 1		# the save completed ok
			except wtslib.sqlError:
				print "An exception occurred in trying to save"
				print "the data to the database.  The following"
				print "message was returned:"
				print sys.exc_value
			except TrackRec.error:
				print "Data validation discovered one or more"
				print "errors in the data file.  The errors"
				print "were:"
				for err in wtslib.string_To_List (sys.exc_value,
					TrackRec.error_separator):
					print "*  %s" % err
			except TrackRec.notLocked:
				print "The current user (%s) does not have" % \
					os.environ ['REMOTE_USER']
				print "a lock on this tracking record.  The"
				print "data cannot be saved now.  The following"
				print "message was returned:"
				print sys.exc_value
			except IndexError:
				print "An unexpected fatal error occurred in"
				print "accessing the database -- this tracking"
				print "record no longer exists in the database."

		# if we encountered any errors, then "finished" remains at 0,
		# and we must give the user the option of fixing the errors or
		# just giving up.

		if not finished:
			print 'Would you like to Fix the problems or',
			print 'Abort the process?  (F/A)'

			if get_initial_char ('FA') == 'A':
				finished = 1	# user wants to abort, so quit

	tf.erase ()	# since we made it out of the loop, we can now clean up
			# the template file (erase it)

	try:
		tr.unlock ()		# finally, unlock the tracking record
	except TrackRec.notLocked:
		pass		# at this point, we know that we have either
				# successfully saved the tracking record or
				# aborted, so we can just ignore this exception
	return


def new_Tracking_Record (
	tr			# the TrackRec object for the tracking record
				# to be edited.
	):
	# Purpose: provides a means for creating new tracking records via the
	#	command line and then saving the information if desired.
	# Returns: nothing
	# Assumes: The current user has write permission for the current
	#	directory.
	# Effects: Creates a text file with the data from tr.  Starts up a
	#	text editor and loads in the text file for the user to edit.
	#	Once the user has exited the editor, prompt to ask if changes
	#	in the text file should be imported to WTS or not.  Then,
	#	import if it was desired.
	# Throws: nothing

	# generate a unique filename in this directory.  These filenames are of
	# the form wts.new.*

	tempfile.tempdir = "."			# work in current dir
	tempfile.template = "wts.new."		# filename stub
	filename = tempfile.mktemp ()		# generate the unique filename

	tf = genTemplateFile (tr, filename)	# get a Template_File object

	# keep going until we have reached a definite finish to the editing
	# process...  (either it imported successfully, or the user declined
	# to import it)

	finished = 0		# not finished yet -- we've just started

	while not finished:
		saveFlag, entries = editAndImportTemplate (tf)

		if not saveFlag:
			finished = 1	# don't try to save, just skip it
		else:
			try:
				# save the basic tracking record

				validateAndSave (entries, tr)

				finished = 1		# the save completed ok

				print "Your file was successfully imported"
				print "and was assigned tracking record number:"
				print "TR%s" % tr.num ()

			except wtslib.sqlError:
				print "An exception occurred in trying to save"
				print "the data to the database.  The following"
				print "message was returned:"
				print sys.exc_value
			except TrackRec.error:
				print "Data validation discovered one or more"
				print "errors in the data file.  The errors"
				print "were:"
				for err in wtslib.string_To_List (sys.exc_value,
					TrackRec.error_separator):
					print "*  %s" % err

			# exceptions TrackRec.notLocked and IndexError should
			# only happen when editing existing tracking records,
			# so we don't need to catch them here.

		# if we encountered any errors, then "finished" remains at 0,
		# and we must give the user the option of fixing the errors or
		# just giving up.

		if not finished:
			print 'Would you like to Fix the problems or',
			print 'Abort the process?  (F/A)'

			if get_initial_char ('FA') == 'A':
				finished = 1	# user wants to abort, so quit

	tf.erase ()	# since we made it out of the loop, we can now clean up
			# the template file (erase it)
	return


def cleanTrackRecNumber (
	tr			# string containing the tracking record number
				# to be cleaned up
	):
	# Purpose: clean up a tracking record number entered on the command line
	# Returns: an integer which is the tracking record number in "tr"
	# Assumes: nothing
	# Effects: strips out any 'T', 'R', and ' ' characters from "tr", and
	#	then converts the remainder to an integer.
	# Throws: propagates a ValueError if we cannot convert "tr" to a simple
	#	integer
	# Notes: strip spaces and the T & R characters using string.translate()

	return string.atoi (string.translate (tr,
		string.maketrans ('',''), 'TR '))


def fixClosure (
	tr_num		# integer; TR num in the connected component where we'd
	):		# like to patch the transitive closure
	# Purpose: patch up the transitive closure (if needed) of the connected
	#	component containing "tr_num"
	# Returns: nothing
	# Assumes: db's SQL routines have been initialized
	# Effects: updates the relationships table in the database to reflect
	#	the proper transitive closure, writes results to stdout
	#	explaining what was changed
	# Throws: propagates wtslib.sqlError if problems occur in querying the
	#	database

	# update the transtive closure and get the ArcSets of Arcs which were
	# added and deleted

	added, deleted = TrackRec.updateTransitiveClosure (tr_num,
		TrackRec.DEPENDS_ON)

	added_arcs = added.getArcs ()		# list of Arc objects added
	deleted_arcs = deleted.getArcs ()	# list of Arc objects deleted

	if (len (added_arcs) == 0) and (len (deleted_arcs) == 0):
		print "No problems found"
	else:
		print "Added %d transitive closure arcs" % len (added_arcs)
		for arc in added_arcs:
			print "\t%d to %d" % (arc.getFromNode(),
				arc.getToNode ())
		print "Deleted %d transitive closure arcs" % len (deleted_arcs)
		for arc in deleted_arcs:
			print "\t%d to %d" % (arc.getFromNode(),
				arc.getToNode ())
	return


def showLocks ():
	# Purpose: show a text table of information about all the locked
	#	tracking records
	# Returns: nothing
	# Assumes: nothing
	# Effects: uses TrackRec module to get info from the database, then
	#	formats and sends to stdout
	# Throws: nothing

	try:
		locks = TrackRec.lockedTrackRecList ()	# get locking info

		# define our table format and headings

		format = "%-6s %-10s %-22s %s"
		heading1 = ('TR #', 'Locked By', 'Locked When', 'Title')
		heading2 = ('----', '---------', '-----------', '-----')

		print format % heading1		# print the table header
		print format % heading2

		for row in locks:		# and, print the table rows
			print format % row

	except wtslib.sqlError:
		error ("Errors occurred while contacting the database")
		sys.exit (ERR_DATABASE)
	return


def updateRouting (
	category	# Category object which should be updated
	):
	# Purpose: allow the user to edit the e-mail and staff lists for the
	#	given "category"
	# Returns: nothing
	# Assumes: nothing
	# Effects: writes prompts to stdout, reads from stdin, updates the
	#	Category info in the database, updates the help file for
	#	the routing categories.
	# Throws: propagates wtslib.sqlError if we have problems querying or
	#	updating the database

	print 'Updating routing options for "%s"' % category.getName ()

	# first, let's update the e-mail list:

	print 'Current e-mail list is: "%s"' % category.getEmail ()
	print 'Please do one of the following:'
	print '\t* Enter a new string of comma-separated addresses'
	print '\t* Enter "None" if you want no e-mails for this category'
	print '\t* Enter a blank string to keep the e-mail list as-is'

	done = 0
	while not done:
		input = string.strip (raw_input ('>'))
		if input == '':
			done = 1
		elif string.upper (input) == 'NONE':
			category.setEmail ('')
			done = 1
		else:
			if category.setEmail (input):
				done = 1
			else:
				print "Could not parse string.  Please check "
				print "that it is a comma-separated list of "
				print "e-mail addresses and try again."

	# next, let's update the staff list:

	print 'Current staff list is: "%s"' % category.getStaff ()
	print 'Please do one of the following:'
	print '\t* Enter a new string of comma-separated staff members'
	print '\t* Enter "None" if you want no staff in this category'
	print '\t* Enter a blank string to keep the staff list as-is'

	done = 0
	while not done:
		input = string.strip (raw_input ('>'))
		if input == '':
			done = 1
		elif string.upper (input) == 'NONE':
			(noErrors, error_strings) = category.setStaff ('')
			if noErrors:
				done = 1
			else:
				print "The following errors were encountered:"
				for error in error_strings:
					print "\t* %s" % error
				print "Please try again."
		else:
			(noErrors, error_strings) = category.setStaff (input)
			if noErrors:
				done = 1
			else:
				print "The following errors were encountered:"
				for error in error_strings:
					print "\t* %s" % error
				print "Please try again."
	category.save ()
	return

def setField (
	TR,		# string; valid TR #
	field,		# string; fieldname from TrackRec.ATTRIBUTES
	value		# string; what we want to set the value to
	):
	# Purpose: update the value of 'field' in the given 'TR'
	# Returns: nothing
	# Assumes: nothing
	# Effects: updates the database
	# Throws: propagates any exceptions raised
	# Notes: We provide intelligent handling of '+' or '-' before the
	#	terms of multi-valued controlled vocabulary fields

	tr = TrackRec.TrackRec (TR)
	if tr.setAttribute (field, value) == 0:
		raise cmdError, \
			'Failed -- could not set %s for %s' % (field, TR)

	vals = TrackRec.validate_TrackRec_Entry (tr.dict())
	tr.set_Values (vals)
	tr.lock()
	tr.save()
	tr.unlock()

	return


def getField (
	TR,		# string; valid TR #
	field		# string; fieldname from TrackRec.ATTRIBUTES
	):
	# Purpose: retrieves the value of 'field' in the given 'TR'
	# Returns: nothing
	# Assumes: nothing
	# Effects: queries the database
	# Throws: propagates any exceptions raised

	tr = TrackRec.TrackRec (TR)
	return tr.getAttribute (field)


def addNoteFromFile (
	TR,		# string; valid TR number
	filename	# full path to file to add as a note
	):
	# Purpose: add the contents of the file specified by 'filename' as a
	#	date-stamped Progress Note for the given TR
	# Returns: nothing
	# Assumes: nothing
	# Effects: updates database, reads from file system
	# Throws: propagates any exceptions

	tr = TrackRec.TrackRec (TR)
	tr.lock()
	try:
		fp = open (filename, 'r')	# read the file
		lines = fp.readlines()
		fp.close()
	except IOError:
		error ("Cannot read input file '%s'" % filename)
		sys.exit (ERR_READFILE)
		return

	entry = '''<LI><B>%s %s</B><BR>
%s<P>
''' % (time.strftime ("%m/%d/%y %H:%M", time.localtime (time.time())), \
	os.environ['REMOTE_USER'],
	string.join (lines, '')
	)

	notes = getField (TR, "Progress Notes")
	if notes in [ '<PRE>\n\n</PRE>', '<PRE>\nNone\n</PRE>' ]:
		notes = '<OL></OL>'

	end = max (string.rfind(notes, '</OL>'), string.rfind(notes, '</ol>'))
	if end != -1:
		notes = notes[:end] + entry + notes[end:]
	else:
		notes = notes + entry
	
	tr.unlock()
	setField (TR, "Progress Notes", notes)
	print "Progress Notes for TR %s updated" % TR
	return


def addNote (
	TR		# string; valid TR number
	):
	# Purpose: pop open the user's editor of choice with a temporary file
	#	for entering a progress note, once he/she saves it, ask the
	#	user if he/she wants to add the contents of the file as a
	#	date-stamped Progress Note for the given TR
	# Returns: nothing
	# Assumes: nothing
	# Effects: updates database, reads from file system, makes system call
	#	to the editor
	# Throws: propagates any exceptions
	
	tr = TrackRec.TrackRec (TR)
	tr.lock()
	locked = 1

	tempfile.tempdir = "."		# work in current dir
	tempfile.template = "note."	# filename stub
	filename = tempfile.mktemp()	# generate a unique filename

	os.system (getEditor() + ' ' + filename)

	done = not os.path.exists (filename)
	while not done:
		print "Would you like WTS to..."
		print "	Add the Progress Note,"
		print "	Edit the file again, or"
		print "	Cancel the addition?  (A/E/C)"

		c = get_initial_char ('AEC')
		if c == 'A':
			tr.unlock()
			locked = 0
			addNoteFromFile (TR, filename)
			done = 1
		elif c == 'E':
			os.system (getEditor() + ' ' + filename)
		else:
			done = 1
	if os.path.exists (filename):
		os.remove (filename)
	if locked:
		tr.unlock()
	return


# -- main program --

if __name__ == '__main__':
	options, error_flag = wtslib.parseCommandLine (sys.argv,
		[ 'dir=', 'display=', 'edit=', 'locks', 'new', 'unlock=',
		  'fixTC=', 'tree=', 'simpleTree=', 'routing', 'batchInput=',
		  'getField=2', 'setField=3', 'addNote=', 'newMinimal=2',
		  'queryTitle=', 'addNoteFromFile=2' ])
	try:
		# Now, because of the was the interface is defined, we can only
		# handle one command at a time.  If we got too many or too few
		# options or we found an error, give the user the command
		# options.

		if (error_flag != 0) or (len (options.keys ()) != 1):
			print USAGE

		elif options.has_key ('new'):
			tr = TrackRec.TrackRec ()	# create new TR, and...
			new_Tracking_Record (tr)	# edit it

		elif options.has_key ('display'):
			raw_tr_num = options ['display'][0]
			tr_num = cleanTrackRecNumber (raw_tr_num)
			tr = TrackRec.TrackRec (tr_num)		# load and...
			display_Tracking_Record (tr)		# display

		elif options.has_key ('unlock'):
			raw_tr_num = options ['unlock'][0]
			tr_num = cleanTrackRecNumber (raw_tr_num)
			tr = TrackRec.TrackRec (tr_num)		# load and...
			unlock_Tracking_Record (tr)		# unlock

		elif options.has_key ('edit'):
			raw_tr_num = options ['edit'][0]
			tr_num = cleanTrackRecNumber (raw_tr_num)
			tr = TrackRec.TrackRec (tr_num)		# load and...
			edit_Tracking_Record (tr)		# edit

		elif options.has_key ('fixTC'):
			raw_tr_num = options ['fixTC'][0]
			tr_num = cleanTrackRecNumber (raw_tr_num)
			fixClosure (tr_num)

		elif options.has_key ('simpleTree'):
			raw_tr_num = options ['simpleTree'][0]
			tr_num = cleanTrackRecNumber (raw_tr_num)
			for line in TrackRec.graphTree (tr_num, 0):
				print line

		elif options.has_key ('tree'):
			raw_tr_num = options ['tree'][0]
			tr_num = cleanTrackRecNumber (raw_tr_num)
			for line in TrackRec.graphTree (tr_num, 1):
				print line

		elif options.has_key ('locks'):
			showLocks ()

		elif options.has_key ('dir'):
			out_string = 'Project Directory for TR%d is: %s'
			raw_tr_num = options ['dir'][0]
			tr_num = cleanTrackRecNumber (raw_tr_num)
			base_dir = TrackRec.getBaseDir (tr_num)
			if base_dir is None:
				print out_string % (tr_num, 'None')
			else:
				print out_string % (tr_num,
					TrackRec.directoryPath (base_dir))

		elif options.has_key ('routing'):
			category = get_Category (
				'Maintenance for which routing category:')
			updateRouting (category)

		elif options.has_key ('batchInput'):
			batchInput.batchInput (options ['batchInput'][0])

		elif options.has_key ('getField'):
			[raw_tr_num, field] = options['getField']
			print getField (raw_tr_num, field)

		elif options.has_key ('setField'):
			[raw_tr_num, field, value] = options['setField']
			setField (raw_tr_num, field, value)

		elif options.has_key ('addNote'):
			[raw_tr_num] = options['addNote']
			addNote (raw_tr_num)

		elif options.has_key ('queryTitle'):
			[value] = options['queryTitle']
			print TrackRec.queryTitle (value)

		elif options.has_key ('addNoteFromFile'):
			[raw_tr_num, filename] = options['addNoteFromFile']
			addNoteFromFile (raw_tr_num, filename)

		elif options.has_key ('newMinimal'):
			[title, status] = options['newMinimal']
			trkey = createMinimalTR (title, status)
			print 'Created new TR%s' % trkey

	except ValueError:
		error ("Cannot parse tracking record number %s" % raw_tr_num)
		sys.exit (ERR_PARSING)

	except TrackRec.alreadyLocked:
		error ("Tracking record TR%s was %s" % (tr_num,sys.exc_value))
		sys.exit (ERR_LOCKED)

	except TrackRec.error, message:
		error (message)
		sys.exit (ERR_TR)

	except IOError:
		error ("Cannot open file '%s'" % options ['batchInput'][0])
		sys.exit (ERR_READING)

	except IndexError:
		error ("Cannot find TR in database")
		sys.exit (ERR_MISSING)

	except cmdError, message:
		error (message)
		sys.exit (ERR_CMDLINE)
