#!/usr/local/bin/python

# Program: tr.query.results.cgi
# Purpose: to parse field and values specifications for tracking records, and
#	use them to query the database and return a tracking record Query
#	Results Summary Screen
# User Requirements Satisfied by This Program:
#	see original WTS User Requirements Document, functional requirements
#	5.4-5.6, 6.1-6.3, 12
# System Requirements Satisfied by This Program:
#	Usage: Call only as a CGI script as part of the WTS web interface, with
#		parameters provided via a GET or POST submission.
#	Uses: Python 1.4
#	Envvars: none
#	Inputs: All fields from a tracking record query form which were filled
#		in.  (Blank fields are not submitted via a POST operation.)
#		These may include any of the following:
#		These include the following tracking record fields:
#			TR_Nr		Title		Needs_Attention_By
#			Area		Type		Requested_By
#			Priority	Status		Status_Date
#			Size		Staff		Directory
#		And these other fields:
#			Primary - string name of the primary field to sort by
#			Primary_Order - 'asc' to sort using Primary in
#				ascending order, or 'desc' for descending
#			Secondary - string name of the second field to sort by
#				(when values for Primary match)
#			Secondary_Order - 'asc' to sort using Secondary in
#				ascending order, or 'desc' for descending
#			Tertiary - string name of the second field to sort by
#				(when values for Primary and Secondary match)
#			Tertiary_Order - 'asc' to sort using Tertiary in
#				ascending order, or 'desc' for descending
#			Text_Fields - string value to look for in the large
#				text fields (Project Definition, Progress Notes)
#			Modification_Date - specifies a date range (a string)
#				which indicates when the tracking records were
#				last saved
#			Displays - a set of strings (combined to a single comma
#				separated string by FieldStorage_To_Dict())
#				that tells us which fields to show in the
#				result table
#			X_Depends_On - checkbox which, if submitted, means we
#				should also include in the result table all
#				ones on which those in the query results depend
#			Depends_On_X - checkbox which, if submitted, means we
#				should also include in the result table all ones
#				which depend on those in the query results
#			Not - a set of strings (combined into a single comma
#				separated string by FieldStorage_to_Dict())
#				that tells us which "Not" boxes were checked on
#				the query form, if any
#		Note that FieldStorage_To_Dict() also converts underscores in
#		the fieldnames to be spaces.
#	Outputs: May generate an HTML screen with reports of various data
#		validation errors, if any occurred, and giving him/her the
#		choice of going back to fix them or of aborting the querying
#		process.  Or, if the data is successfully validated, it will be
#		used to generate and run queries to get selected information
#		about tracking records from the database.  This info is then
#		use to produce an HTML screen with a table of the query
#		results.  The left most column in the table provides a checkbox
#		for each row (a single tracking record) which may be checked to
#		select that tracking record for another type of operation
#		(Redisplay, Grid, or Detail).  The other columns vary depending
#		on the contents of the Display field, but will include whatever
#		tracking record fields were specified.  A Redisplay button will
#		show the same grid, but only those rows which were checked.  A
#		Grid button will produce a grid of tracking records by area.  A
#		Detail button provides detail displays for each checked tracking
#		record.  A WTS Home button will return us to the WTS Home Page.
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
import TabFile		# used to generate a tab-delimited file

# --- definition of a defaults for selecting fields and sorting results ---

# If this CGI script is invoked from the tracking record query form, then
# we already have information about which fields to display and how to sort
# the results.  If we came in from one of the quick-queries on the WTS Home
# Page, however, we just need to use some default values.  We define them
# in this dictionary:

hidden_field_values = {

	# fields to display in columns:

	'Displays'		: 'TR Nr,Title,Area,Type,Status',

	# sorting information - three levels of sorting, only one of which
	# is actually defined.  (the other two are unnecessary and set to
	# None, as the tracking record number is always unique):
	#	sort by tracking record number, ascending order

	'Primary'		: 'TR Nr',
	'Primary Order'		: 'asc',
	'Secondary'		: 'None',
	'Secondary Order'	: 'asc',
	'Tertiary'		: 'None',
	'Tertiary Order'	: 'asc'
	}

# --- body of the script ---

try:
	form = cgi.FieldStorage ()			# input from GET / POST
	dict = wtslib.FieldStorage_to_Dict (form)	# convert to dictionary

	# Do a quick error check to see if we were called from the WTS Home
	# Page as a result of the "Retrieve with Descendants" button by the
	# "Find TR #" box.  If so, we need to make sure that we have something
	# in the 'tr nr' field.

	dict_keys = dict.keys()
	if os.environ.has_key ('HTTP_REFERER') and \
		string.find (os.environ['HTTP_REFERER'], 'query.html') == -1 \
		and len(dict) == 1 \
		and dict_keys[0] == 'X Depends On':
			screenlib.gen_Message_Screen (
				'WTS: No Tracking Records to Display',
				'''No records were selected for display.
				Please press Ok to go back to the previous
				screen.''', 1)
			raise SystemExit

	# Look for the special case in the input data:  If Staff or Requested By
	# is set to be 'REMOTE_USER', then it is requesting that we fill in the
	# remote user's name.  The need to do this arose from the quick-queries
	# on the WTS Home Page - we needed to restrict queries by the current
	# user's name.  This information is found in the environment variable
	# 'REMOTE_USER'.

	for field in ['Staff', 'Requested By']:
		if dict.has_key(field) and (dict [field] == 'REMOTE_USER'):

			# if the field existed and if it contained the special
			# request, then replace its value with the current
			# user's name

			dict [field] = os.environ ['REMOTE_USER']

	# Validate the entries in this dictionary.  If any errors are
	# discovered in validation, an exception is raised in the
	# validate_Query_Form function.

	try:
		clean_dict = TrackRec.validate_Query_Form (dict)
		valid = 1	# no errors found - data is valid
	except TrackRec.error:
		valid = None	# errors were found - data is invalid

		# When the exception was raised, the list of errors was passed
		# back in a single string (separated with the standard
		# "error_separator" defined in TrackRec) in exc_value.  We need
		# to convert this back to a list of error strings and pass it to
		# the error notification screen to give the user the full info
		# about what errors were discovered.

		errors = wtslib.string_To_List (sys.exc_value,
				TrackRec.error_separator)

		doc = screenlib.Error_Screen ()	# create the error screen
		doc.setup (errors)		# setup it up w/ list of errors
		doc.write ()			# write it out

	if valid:
		clean_keys = clean_dict.keys ()	# get a list of the keys from
						# the validated dictionary

		# let's go through the default values for the hidden fields
		# (those used in selecting fields and sorting).  Check each
		# one.  When this loop ends, hidden_field_values will have
		# the values that will be used in producing the results.  This
		# information is important because it needs to be passed along
		# as hidden fields on the query results screen to ensure that
		# "redisplays" of that screen will use the same columns and
		# ordering.

		for key in hidden_field_values.keys ():
			if key not in clean_keys:

				# if it is not in the cleaned dictionary, then
				# we need to use the default value and add it
				# to the list of defined, cleaned keys.

				clean_dict [key] = hidden_field_values [key]
				clean_keys.append (key)
			else:
				# remember the value that was defined

				hidden_field_values [key] = clean_dict [key]

		# since the entries are valid, use them to generate and run
		# SQL statements to query the database.

		results = TrackRec.build_And_Run_SQL (clean_dict)

		# These results could have multiple rows per tracking record
		# because of the many-to-many relationships in several fields.
		# Clean these results up, and condense them, so that all the
		# information for a tracking record is contained in only one
		# result row.

		clean_results = TrackRec.parse_And_Merge (results, 'TR Nr')

		if clean_dict.has_key ('As Text'):
			# send out the results as a tab-delimited text file

			t = TabFile.TabFile ()
			t.setList (clean_results)
			print "Content-type: text/plain"
			print
			if str(t) == '':
				print "No tracking records were selected"
			else:
				print "# Current info as of %s" % \
					wtslib.current_Time ()
				print "#"
				print t
		else:
			if dict.has_key ('Status Date'):
				sd = dict ['Status Date']
			else:
				sd = None

			# use these cleaned up results and the dictionary
			# of hidden fields (sorting & selecting info) to
			# generate the query result screen.

			doc = screenlib.Query_Result_Screen ()
			doc.setup (clean_results, hidden_field_values, sd)
			doc.write ()

	# if the entries were not valid, then we have already displayed an
	# error screen.  So, we don't need an else clause.

except SystemExit:
	pass
except:
	screenlib.gen_Exception_Screen ('tr.query.results.cgi')
