#!/usr/local/bin/python

# wtslib.py - provides standard routines used commonly across WTS modules

'''
# Author:
#	Jon Beal
# Date written:
#	4-23-98			began initial implementation
# Summary:
#	provides a set of common routines which are used across multiple WTS
#	modules (bin, lib, and cgi).  By pulling those routines into a single
#	file, we provide a single point of maintenance.
# Requirements:
#	* provide a consistent functional interface to all WTS modules
# DateTime-Related Functions:
#	parse_DateRange (daterange string)
#	parse_DateTime (datetime string)
#	parse_Date (date string)		* internal use only
#	parse_Time (time string)		* internal use only
# Other Functions:
#	FieldStorage_to_Dict (FieldStorage object)
#	underscored (string to have spaces coverted to underscores)
#	current_Time ()
#	list_To_String (list of items, string separator)
#	string_To_List (string of comma-space separated items, string separator)
#	duplicated_DoubleQuotes (string to have internal " changed to "")
#	sql (queries, parsers = 'auto')
#	record_SQL_Errors (queries, parsers,	* internal use only
#		exc_type, exc_value, exc_traceback)
#	send_Mail (send_from, send_to, subject,	message)
#       dbValueString (value to format for inclusion in a sql query)
#	parseCommandLine (argv, options)
#	escapeAmps (string)
#	isHTML (string)
#	isPRE (string)
#	wrapLines (string, max line length)
#	splitList (list, maximum integer items per sublist)
'''

import os
import Configuration
import regex
import regsub
import getopt
import string
import tempfile
import time
import traceback
import sys
import types
import db
import smtplib

TRUE = 1
FALSE = 0

OPTIONS_OKAY = 0			# error codes for parseCommandLine()
INVALID_SPECIFICATION = -1
WRONG_ARGUMENTS = -2
MISPLACED_ARGUMENT = -3
MISSING_REQUIRED = -4

error = 'wtslib.error'			# standard exception to be raised by
					# the wtslib module

sqlError = 'wtslib.sqlError'		# global exception value, distinct
					# from the standard "error" exception
					# so we can use special handling when
					# trapping for database errors.

SENDMAIL = '/usr/lib/sendmail'		# path to the standard sendmail program


#---DATE AND TIME FUNCTIONALITY------------------------------------------

# global date and time values

YEAR_SPLIT = 90			# 2 digit years >= 90 are in 1900, else 2000
FIRST_MINUTE = ' 12:00 AM'	# first minute of a day
LAST_MINUTE = ' 11:59 PM'	# last minute of a day

# let's define a dictionary with month name (and abbreviation) to
# month number mappings.  This should be global so that we don't take time
# to initialize it on every attempt to parse a date (if multiple dates need
# to be parsed within a single module):

MONTH_MAP = {	'january' : 1,		'jan' : 1,
		'february' : 2,		'feb' : 2,
		'march' : 3,		'mar' : 3,
		'april' : 4,		'apr' : 4,
		'may' : 5,		'may' : 5,
		'june' : 6,		'jun' : 6,
		'july' : 7,		'jul' : 7,
		'august' : 8,		'aug' : 8,
		'september' : 9,	'sep' : 9,	'sept' : 9,
		'october' : 10,		'oct' : 10,
		'november' : 11,	'nov' : 11,
		'december' : 12,	'dec' : 12 }

# let's also define a simple dictionary which maps month numbers to the
# maximum number of days in that month.  At this point, let's not do any
# fancy handling of leap years, just use 29 for February.  As these are
# only for error checking, it won't throw off any calculations.

MAX_DAYS = {	1 : 31,		2 : 29,		3 : 31,		4 : 30,
		5 : 31,		6 : 30,		7 : 31,		8 : 31,
		9 : 30,		10 : 31,	11 : 30,	12 : 31 }


# let's define a couple of standard regular expression strings which will
# always match whitespace at the start and at the end of a string:

START = '^[ \t]*'	# regex match to start of string, whitespace ok
END = '[ \t]*$'		# regex match to end of string, whitespace ok


#---DATE AND TIME FUNCTIONS----------------------------------------------

def parse_Date (date):
	''' returns a tuple (standardized date string, list of error strings)
	#
	# Requires:	date - string; represents a date (no time components)
	# Format:	recognizes dates of the forms:
	#			mm/dd/yy	mm/dd/yyyy
	#			dd MMM yy	dd MMM yyyy
	#			MMM dd yy	MMM dd yyyy
	#			MMM dd, yy	MMM dd, yyyy
	#		(where MMM is the text name of the month)
	# Effects:	Parses date and converts it to the standard WTS date
	#		format (mm/dd/yyyy).  Maintains a list of any errors
	#		encountered in parsing.  Returns a tuple with either:
	#		(date string, None) if no errors, or ('', list of
	#		error strings) if errors were found
	# Modifies:	no side effects
	'''
	global START, END, MONTH_MAP, MAX_DAYS, YEAR_SPLIT

	# we use regular expressions to do our initial examination and
	# splitting of date into its component pieces.  Set up the regex
	# strings we'll use:

	re_day = '\([ 0123]?[0-9]\)'	# optional tens digit, then ones digit
	re_month = '\([ 01]?[0-9]\)'	# optional tens digit, then ones digit
	re_monthName = (
		'\([a-zA-Z]'		# must have at least three letters
		'[a-zA-Z][a-zA-Z]+\)'
		)
	re_year = (
		'\(19[0-9][0-9]\|'	# 19yy --> 1900's, or
		'20[0-9][0-9]\|'	# 20yy --> 2000's, or
		'[0-9][0-9]\)'		# just yy - no century
		)

	# now, compile the regular expressions to look for recognizable date
	# formats (for a list, see above):

	format1 = regex.compile (START + re_month + '/' + re_day + '/' + 
		re_year + END)
	format2 = regex.compile (START + re_day + ' +' + re_monthName + ' +' + 
		re_year + END)
	format3 = regex.compile (START + re_monthName + ' +' + re_day + ',? +' +
		re_year + END)

	# now, see if we can extract month, day, and year using any of the
	# above-listed recognized formats:

	errors = []			# found no errors yet
	month = None			# no month yet
	day = None			# no day yet
	year = None			# no year yet

	# is it:  month/day/year (all numeric)

	if format1.match (date) >= 0:
		(month, day, year) = format1.group (1, 2, 3)
		month = string.atoi (month)
		if (month < 1) or (month > 12):
			errors.append ('Month out of range: %d' % month)

	# is it:  day monthName year

	elif format2.match (date) >= 0:
		(day, monthName, year) = format2.group (2, 1, 3)
		monthName = string.lower (monthName)
		if MONTH_MAP.has_key (monthName):
			month = MONTH_MAP [monthName]
		else:
			errors.append ('Unrecognized month: %s' % monthName)

	# is it:  monthName day, year

	elif format3.match (date) >= 0:
		(monthName, day, year) = format3.group (1, 2, 3)
		monthName = string.lower (monthName)
		if MONTH_MAP.has_key (monthName):
			month = MONTH_MAP [monthName]
		else:
			errors.append ('Unrecognized month: %s' % monthName)

	# if we didn't recognize a format, just give up

	else:
		return ('', [ 'Could not recognize date %s' % date ])

	# now, get integer values for day and year.  validate the day value.
	# promote a two-digit year to four digits, based on YEAR_SPLIT.

	day = string.atoi (day)
	year = string.atoi (year)

	if MAX_DAYS.has_key (month):
		if (day < 1) or (day > MAX_DAYS [month]):
			errors.append ('Day %d out of range for month %d' %
				(day, month))

	if (year / 100) == 0:
		if year < YEAR_SPLIT:
			year = year + 2000
		else:
			year = year + 1900

	# return appropriately, based on whether we found errors or not:

	if len (errors) > 0:
		return ('', errors)
	else:
		return ('%s/%s/%s' % (string.zfill (month, 2),
			string.zfill (day, 2), str (year)), None)


def parse_Time (tym):
	''' returns a tuple (standardized time string, list of error strings)
	#
	# Requires:	tym - string; a time (HH:MM PM) where the AM/PM
	#		designation is optional
	# Effects:	parses tym and converts it to the standard WTS time
	#		format (HH:MM PM).  Maintains a list of any errors
	#		encountered in parsing.  Returns a tuple with either:
	#		(time string, None) if no errors, or ('', list of error
	#		strings) if errors were found.
	# Modifies:	no side effects
	'''
	global START, END

	# we use regular expressions to do our initial examination and
	# splitting of tym into its component pieces.  Set up the regex
	# strings we'll use:

	re_ampm = '\([AP]M\)'				# AM/PM
	re_hhmm = '\([012 ]?[0-9]\):\([0-5][0-9]\)'	# HH:MM

	# now, compile the regular expressions to look for recognizable tym
	# formats (for description, see above):

	timeampm = regex.compile ('.*' + re_ampm)	# is AM/PM anywhere?
	time = regex.compile (START + re_hhmm + END)	# time without AM/PM
	fulltime = regex.compile (START + re_hhmm + 
		'[ \t]*' + re_ampm + END)		# time with AM/PM

	ampm = None		# no AM/PM designation yet
	hours = None		# no hours yet
	minutes = None		# no minutes yet

	# now, try to match tym to one of the formats (one with AM/PM, one
	# without)

	if (timeampm.match (tym) >= 0):
		if (fulltime.match (tym) >= 0):
			(hours, minutes, ampm) = fulltime.group (1, 2, 3)
	elif (time.match (tym) >= 0):
		(hours, minutes) = time.group (1, 2)

	# if hours is still None, then we know it didn't match.  bail out.

	if not hours:
		return ('', [ 'Could not recognize time: %s' % tym ])

	# otherwise, we have no errors yet.  So, get integer values for hours
	# and minutes.  Then error-check the hours.  Because of the regular
	# expression matching [0-5][0-9], we know that minutes must be in the
	# correct range (00-59).

	errors = []
	hours = string.atoi (hours)
	minutes = string.atoi (minutes)

	if (hours < 1) or (hours > 23):
		errors.append ('Hours out of range: %d' % hours)

	# if ampm not yet defined, then set the AM/PM designation and adjust
	# the hours if necessary (convert 24-hour clock to 12-hour)

	if not ampm:
		if (hours >= 12):
			ampm = 'PM'
			if (hours > 12):
				hours = hours - 12
		else:
			ampm = 'AM'

	# otherwise, check that the designation is correct.  Note that a PM
	# designation with hours > 12 is not necessarily incorrect, but rather
	# just redundant.  (so adjust it to reflect a 12-hour clock)

	else:
		if (ampm == 'AM') and (hours > 12):
			errors.append ('AM designation is incorrect for ' + \
				'%d hours' % hours)
		elif (ampm == 'PM') and (hours > 12):
			hours = hours - 12

	# now, return appropriate tuple

	if len (errors) > 0:
		return ('', errors)
	else:
		return (('%s:%s %s' %
			(string.zfill(hours,2), string.zfill(minutes,2), ampm),
			None))


def parse_DateRange (dates):
	''' returns a tuple with (start datetime, stop datetime, list of error
	#       strings).  either start or stop datetime may be ''.
	#
	# Requires:     dates - string; contains a single date or a range
	#               of dates, specified with .., ..., or -.  Ranges may
	#               be open ended by having the marker before or after
	#               a single date.  Times are not accepted - only dates.
	#               dates may also be just a single date value which
	#               implies a date range which includes just that day.
	# Format:	recognizes a date in the following forms:
	#			mm/dd/yy	mm/dd/yyyy
	#			dd MMM yy	dd MMM yyyy
	#			MMM dd, yy	MMM dd, yyy
	#		(where MMM is the text name of the month)
	# Effects:      parses the input string and returns a tuple of the
	#               form:  (starting datetime string, stopping datetime
	#               string, None) if no errors were found, or ('', '',
	#               list of error strings) if errors were found.  Each
	#		datetime string returned is of the format:
	#			mm/dd/yyyy HH:MM PM
	# Modifies:     no side effects
	'''
	# Let's define two regular expressions which should catch the 
	# delimiters (.., ..., -) if they exist in dates.

	re_delim1 = regex.compile (
		'\([^\.]*\)'		# group 1 = any non-period characters
		'\.\.\.?'		# separated by 2 or 3 periods
		'\([^\.]*\)')		# group 2 = any non-period characters
	re_delim2 = regex.compile (
		'\(.*\)'		# group 1 = any characters
		'-'			# separated by a hyphen
		'\(.*\)')		# group 2 = any characters

	# now, try to pick out temp_start and temp_stop (the raw start and
	# stop dates, before processing).  If there is no date on either side
	# of the delimiter, the field will be filled in as ''.

	found_marker = 1		# assume that we will find a marker

	if re_delim1.match (dates) >= 0:
		(temp_start, temp_stop) = re_delim1.group (1, 2)
	elif re_delim2.match (dates) >= 0:
		(temp_start, temp_stop) = re_delim2.group (1, 2)
	else:
		temp_start = dates	# assume dates is really a single date
		temp_stop = ''		# fill this in later
		found_marker = None	# note that we didn't find a marker

	# if both the temp_start and temp_stop dates are empty strings, then
	# we only had a marker.  We should bail out with an error message.

	if found_marker and (len (temp_start) == 0) and (len (temp_stop) == 0):
		return ('', '', ['Only found a marker without a date'])

	# now, try to interpret start_date and stop_date (if they are not
	# empty):

	start_date = ''			# no start date yet
	stop_date = ''			# no stop date yet
	start_date_errors = None	# no errors in start date yet
	stop_date_errors = None		# no errors in stop date yet

	if (len (temp_start) > 0):
		start_date, start_date_errors = parse_Date (temp_start)
	if (len (temp_stop) > 0):
		stop_date, stop_date_errors = parse_Date (temp_stop)

	# collect the error sets:

	errors = []			# assume no errors
	for err_list in [ start_date_errors, stop_date_errors ]:
		if err_list:
			errors = errors + err_list

	# now, if we found any errors, just return them:

	if (len (errors) > 0):
		return ('', '', errors)

	# if we didn't find a marker, then we can now assume that the stopping
	# date is the same as the starting date:

	if not found_marker:
		stop_date = start_date

	# and finally, return appropriate values for three cases:
	#	1. have no start date and no stopping date (should not happen)
	#	2. have no start date, but have a stopping date
	#	3. have a start date, but have no stopping date
	#	4. have both a start date and a stopping date

	if (start_date == '') and (stop_date == ''):
		return ('', '', [ 'No date found' ])
	elif start_date == '':
		return ('', stop_date + LAST_MINUTE, None)
	elif stop_date == '':
		return (start_date + FIRST_MINUTE, '', None)
	else:
		return (start_date + FIRST_MINUTE, stop_date + LAST_MINUTE, 
			None)


def parse_DateTime (datetime):
	''' returns a tuple (standardized datetime string, list of error
	#	strings)
	#
	# Requires:	datetime - string; a single date or datetime value.
	# Effects:	parses the input datetime string and returns a tuple
	#		with either:  (standardized datetime string, None) if
	#		no errors were found, or ('', list of error strings)
	#		if errors were found.
	# Format:	a datetime string is recognized as a single date or a
	#		date followed by one or more spaces and then a time.
	#		A date is recognized in the following forms:
	#			mm/dd/yy	mm/dd/yyyy
	#			dd MMM yy	dd MMM yyyy
	#			MMM dd, yy	MMM dd, yyy
	#		(where MMM is the text name of the month)
	#		A time is recognized in the form:  HH:MM PM
	#		(The AM/PM designation is optional.)
	# Modifies:	no side effects
	'''
	global FIRST_MINUTE

	# get a local copy of datetime that we can butcher (and strip all
	# extraneous spaces from the ends)

	local_datetime = string.strip (datetime)

	# now, we need to find out if we have a date only, or a date and a
	# time.  If there is a time, then it must have a colon, so that's
	# what we'll look for.

	colon_pos = string.find (local_datetime, ':')
	if (colon_pos < 1):

		# we only have a date, so just process that part and return
		# the appropriate values

		temp_date, temp_date_errors = parse_Date (local_datetime)
		if temp_date_errors == None:

			# append a string with the first minute of the day

			return (temp_date + FIRST_MINUTE, None)
		else:
			return ('', temp_date_errors)
	else:
		# we found a time, so we need to process both the date part
		# and the time part.  The time part should begin two characters
		# to the left of the colon, so that's where we'll split the
		# string.

		# if we can't go two before the colon position, then bail out
		split_pos = colon_pos - 2
		if split_pos < 0:
			return ('', ['Could not find a date'])

		temp_date, temp_date_errors = \
			parse_Date (local_datetime [:split_pos])
		temp_time, temp_time_errors = \
			parse_Time (local_datetime [split_pos:])

		# now, combine our error strings:

		if (temp_date_errors == None):
			errors = []
		else:
			errors = temp_date_errors
		if (temp_time_errors <> None):
			errors = errors + temp_time_errors

		# and return the appropriate value based on the errors found

		if errors == []:
			return (temp_date + ' ' + temp_time, None)
		else:
			return ('', errors)


#---NON-DATE & TIME FUNCTIONS--------------------------------------------

def FieldStorage_to_Dict (fs):
	''' accepts a cgi.FieldStorage object, from which it gets the values
	#	and returns them in a dictionary.
	#
	# Requires:	fs - a cgi.FieldStorage object (input from a Get or
	#			Post submission to a CGI script, parsed by
	#			standard python module cgi)
	# Effects:	see above
	# Modifies:	no side effects
	'''
	dict = {}			# the dictionary we're building

	fs_keys = fs.keys ()
	for key in fs_keys:

		# convert underscores in field names to spaces (this is a
		# WTS convention - field names with spaces are included on
		# forms with underscores instead)

		clean_key = string.translate (key, \
			string.maketrans ('_+', '  '), '')

		# if the item is a list, then add each item, separated by
		# commas

		if type (fs [key]) == types.ListType:
			for item in fs [key]:

				# if the key is already there, then we're just
				# adding another value to the string.

				if clean_key in dict.keys ():
					dict [clean_key] = dict [clean_key] + \
						', ' + str (item.value)

				# otherwise, we're adding a new entry to the
				# dictionary

				else:
					dict [clean_key] = str (item.value)

		# otherwise, just get the value

		else:
			dict [clean_key] = fs [key].value
	return dict


def underscored (s):
	''' accepts a string and returns a string with all spaces converted
	#	to underscores
	#
	# Requires:	s - a string
	# Effects:	see above
	# Modifies:	no side effects
	'''
	return string.translate (s, string.maketrans (' ', '_'), '')


def current_Time ():
	''' return a string containing the current date and time in the
	#	standard WTS format:  mm/dd/yyyy HH:MM PM
	#
	# Requires:	nothing
	# Effects:	see above
	# Modifies:	no side effects
	'''
	return time.strftime ('%m/%d/%Y %I:%M %p', \
		time.localtime (time.time ()))


def list_To_String (
	list,			# list of items to include in the string
	separator = ', '	# string used to separate the items in the
				# string we build and return
	):
	# Purpose: take the items in "list" and put their string representations
	#	in a string (separated by the given "separator")
	# Returns: a string as described in Purpose
	# Assumes: items in "list" have string representations -- str() works.
	# Effects: see Purpose
	# Throws: nothing
	# Notes: This is similar to string.join(), but it handles arbitrary
	#	items in "list" as long as they work with the str() function.
	#	(Objects need to define a __str__() method.)
	# Examples:
	#	list_To_String ([ '13', 'hello' ]) ==> '13, hello'
	#	list_To_String ([ 'There is a', 'problem' ], ':::') ==>
	#		'There is a:::problem'

	s = ''
	for item in list:
		s = s + separator + str (item)
	return s [len (separator):]


def string_To_List (
	s,			# string of items separated by comma-space
	separator = ', '	# string used to separate the items in s
	):
	# Purpose: extract comma-space separated items from s and return them
	#	in a list of strings.
	# Returns: if s is a string, then we return a list of the items in s
	#	(stored as individual strings).  Otherwise, return an empty
	#	list.
	# Assumes: nothing
	# Effects: see Returns.
	# Throws: nothing
	# Notes: This function is almost an inverse of list_To_String.  While
	#	list_To_String takes arbitrary items and concatenates their
	#	string representations into a string separated by the given
	#	separator, this function merely extracts the individual string
	#	representations.  It does not convert them back to their
	#	original types.
	# Examples:
	#	string_To_List ('13, hello')  ==> [ '13', 'hello' ]
	#	string_To_List ('There is a:::problem', ':::') ==>
	#		[ 'There is a', 'problem' ]

	if type (s) == types.StringType:
		return string.split (s, separator)
	else:
		return []


def duplicated_DoubleQuotes (s):
	''' returns string s, but with any internal double quotes doubled.
	#
	# Requires:	s - a string
	# Effects:	returns a copy of s, but with any double quotes (")
	#		in the string being doubled ("")
	# Modifies:	no side effects
	'''
	return regsub.gsub ('"', '""', s)


def sql (queries, parsers = 'auto'):
	''' wrapper for db.sql which catches errors & writes diagnostics
	#
	# Assumes:	db has been initialized
	# Requires:	queries - a string or list of strings, each of which is
	#			a SQL query.  (as appropriate for db.sql)
	#		parsers - optional list of parser functions, as 
	#			appropriate for db.sql.  is set to 'auto'
	#			by default, since this is the most used mode
	#			throughout wts.
	# Effects:	passes queries and parsers on to db.sql (see its
	#		documentation).  If no exceptions were raised, just
	#		return the value from db.sql.  If an exception did
	#		occur, catch it, write out some diagnostic information,
	#		then raise a sqlError exception with a value that
	#		identifies the diagnostic file.
	# Modifies:	depends on queries and parsers
	'''
	try:
		return db.sql (queries, parsers)
	except:
		global sqlError
		filename = record_SQL_Errors (queries, parsers, sys.exc_type, \
			sys.exc_value, sys.exc_traceback)
		raise sqlError, 'Error occured in executing query.  ' + \
			'Diagnostics are in ' + filename


def record_SQL_Errors (queries, parsers, exc_type, exc_value, exc_traceback):
	''' creates a new file and writes diagnostic info to it, returns name
	#
	# Requires:	queries - string or list of strings, each of which is
	#			one SQL query
	#		parsers - string 'auto' or list containing possibly
	#			both strings ('auto') and function pointers,
	#			denoting the parsers for the queries. 
	#		exc_type - type of exception which occurred
	#		exc_value - value of the exception which occurred
	#		exc_traceback - the traceback stack when the exception
	#			occurred
	# Effects:	creates a new file in the directory specified in 
	#		configuration item DIAG_DIR, the diagnostics directory.
	#		writes diagnostic information out to it, describing the
	#		exception that occurred while running SQL queries, and
	#		giving the queries themselves.  returns the name of
	#		the file.
	# Modifies:	new file in diagnostics directory
	'''
	trace_tuples = traceback.extract_tb (exc_traceback)

	# We want to create a new file (named wts.sql.*) in the diagnostics
	# directory.  That directory is specified as part of the system
	# configuration.

	tempfile.tempdir = Configuration.config ['DIAG_DIR']
	tempfile.template = "wts.sql."
	filename = tempfile.mktemp ()		# get a unique filename

	fp = open (filename, 'w')

	fp.write ('Exception Type: ' + str (exc_type) + '\n')
	fp.write ('Exception Value:' + str (exc_value) + '\n')
	fp.write ('Exception Traceback:\n--------------------\n ')
	for tuple in trace_tuples:
		file = tuple [0]
		line = str (tuple[1])
		function = tuple [2]
		if tuple [3]:
			lineText = tuple[3]
		else:
			lineText = ''
		fp.write (file + ' : ' + line + ' : ' + function + '\n')
		fp.write ('	' + lineText + '\n')

	fp.write ('\n--------\nQueries:\n--------\n')
	if type (queries) == types.ListType:
		for q in queries:
			fp.write (q + '\n\n')
	else:
		fp.write (queries + '\n\n')

	fp.write ('\n--------\nParsers:\n--------\n')
	if type (parsers) == types.ListType:

		# if the type is a list, then we have a list containing 
		# possibly both strings and function pointers.  With each item,
		# if it is a string we can print it; otherwise use the __name__
		# attribute to print the function's name:

		for p in parsers:
			if type (p) == types.StringType:
				fp.write (p + '\n\n')
			else:
				fp.write (p.__name__ + '\n\n')
	else:
		fp.write (parsers + '\n\n')

	fp.close ()
	return filename

def send_Mail (
	send_from,	# e-mail address sending the message
	send_to,	# e-mail address to which to send the message
	subject,	# e-mail subject line
	message		# text of the e-mail message
	):
	# Purpose: produce and send an e-mail message from send_from to send_to
	#	with the given subject and message
	# Returns: None if sent okay, integer return code from sendmail if not
	# Assumes: global SENDMAIL variable is valid
	# Effects: see Purpose.
	# Throws: nothing

	if not (send_to and send_from):
		return

	if str(send_to) == 'None':
		return

	if str(send_from) == 'None':
		return

	send_from = '%s@informatics.jax.org' % send_from
	send_to = '%s@informatics.jax.org' % send_to

#	global SENDMAIL
#	p = os.popen ("%s -t" % SENDMAIL, "w")
#	p.write ("From: %s\n" % send_from)
#	p.write ("To: %s\n" % send_to)
#	p.write ("Subject: %s\n" % subject)
#	p.write ("\n")
#	p.write ("%s" % message)
#	return p.close ()

	msg = '''From: %s
To: %s
Subject: %s

%s
''' % (send_from, send_to, subject, message)

	server = smtplib.SMTP('smtp.jax.org')
	server.sendmail(send_from, send_to, msg)
	server.quit()
	return

def dbValueString (x):
	''' returns a string which represents x as it should go into a sql
	#       query for processing by sybase.
	#
	# Requires:     x - can be None, a string value, or an integer
	# Effects:      Currently handles None, string values, and integer
	#               values by returning an appropriate string for adding
	#               them to a sql query statement.
	# Modifies:     no side effects
	'''
	if x == None:
		return 'Null'
	elif type (x) == type (''):
		return '"' + duplicated_DoubleQuotes (x) + '"'
	else:
		return str (x)


def splitCommandLineOptions (
	argv			# full list of command line parameters
	):
	# Purpose: process the command line in 'argv' so that quoted items
	#	are part of the same command-line option
	# Returns: list of strings
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Example:
	#	splitCommandLineOptions ( [ 'wts.py', '--setField',
	#		'"this', 'is', 'my' ,'story"' ] )
	#	returns:
	#		[ 'wts.py', '--setField', 'this is my story' ]

	options = []		# list of options found so far
	s = ''			# string to collect options

	for item in argv[1:]:
		# if 's' is non-empty, then we are collecting a quoted item,
		# so just add to it.  Otherwise, replace it.

		if s:
			s = '%s %s' % (s, item)
		else:
			s = item

		if s[0] not in ('"', "'"):	# we don't have a quoted item
			options.append (s)
			s = ''

		elif s[0] == s[-1]:		# we completed a quoted item
			options.append (s[1:-1])
			s = ''
	if s:
		options = ['ERROR: Quote not closed']
	return options


def parseCommandLine (
	args,		# complete sys.argv list
	options		# [ extended GNU-style option name, ... ]
	):
	# Purpose: parse the command-line 'args' according to an allowed set
	#	of 'options'
	# Returns: tuple containing (dictionary of options mapped to lists of
	#	string arguments for each, integer error code)
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes:
	#    extended GNU-style option name:
	#	myOption	option only, no parameters
	#	myOption=	option requires one parameter
	#	myOption=n	option requires n parameters (n >= 0)
	#	*myOption	option is required (can combine with =, =n)

	re = regex.compile ('\(\*?\)'
			'\([A-Za-z0-9_]+\)'
			'\(.*\)'
			)
	optdict = {}		# dict maps option name -> # parms
	required = []		# dict of required option names
	specified = {}		# dict maps option name -> list of parms

	# parse the list of valid options, each in extended GNU-style:

	for opt in options:
		if re.match (opt) != -1:
			optrequired = re.group(1)
			optname = re.group(2)
			tail = re.group(3)
		if optrequired:
			required.append (optname)

		count = 0
		if tail:
			if tail[0] == '=':
				if len(tail) == 1:
					count = 1
				else:
					try:
						count = string.atoi (tail[1:])
					except ValueError:
						return specified, \
							INVALID_SPECIFICATION
		optdict ['--%s' % optname] = count

	# go through args and pull the quoted items together...

	myArgs = splitCommandLineOptions (args)

	# now, go through the 'args' and build the dictionary of options
	# and their respective arguments:

	opt = ''		# the option for which we're collecting args
	for arg in myArgs:
		if optdict.has_key (arg):
			opt = arg[2:]		# cut off the '--'
			specified[opt] = []
		elif not opt:
			return specified, MISPLACED_ARGUMENT
		else:
			specified[opt].append (arg)

	# are any required parameters missing?

	for req in required:
		if not specified.has_key ('--%s' % req):
			return specified, MISSING_REQUIRED

	# do any options have the wrong number of arguments

	for opt in specified.keys():
		if optdict['--%s' % opt] != len(specified[opt]):
			return specified, WRONG_ARGUMENTS

	return specified, OPTIONS_OKAY


def escapeAmps (
	s	# input string, possibly with ampersands
	):
	# Purpose: escape the ampersands in "s" so they will appear properly
	#	when sent out to a browser.
	# Returns: a copy of "s", but with escapes as stated in Purpose
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes: Because of some browser quirks, when we send a string out for
	#	editing to an HTML TextArea, we need to be sure to escape the
	#	ampersands when we want them to appear as ampersands when
	#	displayed.  (The browser iterprets the first level of escaping,
	#	so that a "&lt;" is displayed as "<" and submitted as such.  We
	#	want to keep the "&lt;" in the input.)
	# Example: 
	#	escapeAmps ("here are &lt; some &gt;")
	#		returns:
	#	"here are &amp;lt; some &amp;gt;"

	return regsub.gsub ("&", "&amp;", s)


def isHTML (
	s	# the string to test
	):
	# Purpose: see whether string s contains HTML markups
	# Returns: boolean - TRUE if "s" contains HTML markups, FALSE if not
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes: We do not actually test for the set of valid HTML markups, as
	#	the set is growing and often browser-dependent.  We interpret
	#	any string of letters and slashes between < and > to be an HTML
	#	markup.  We do not look for spaces or numbers in tags, as we
	#	assume that if someone is doing HTML, there will be a typical
	#	letter/slash tag somewhere in it:  <P>, <BR>, <OL>, </A>, etc.
	# Examples: 
	#	isHTML ('Test <bold here>') ==> FALSE
	#	isHTML ('Test <bold here><b>') ==> TRUE
	#	isHTML ('<a href="kelso">') ==> FALSE
	#	isHTML ('<a href="kelso"> click here </a>'> ==> TRUE

	if regex.search ('<[A-Za-z/]+>', s) != -1:
		return TRUE
	return FALSE

def isPRE (
	s	# the string to test
	):
	# Purpose: see whether string s is preformatted text
	# Returns: boolean - TRUE if "s" contains no HTML markups or if it
	#	begins with "<PRE>" and ends with "</PRE>", FALSE otherwise
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes: See the isHTML() function, as it is used here.

	t = string.strip (s)
	if not isHTML (t):
		return TRUE
	elif (t[:5] == "<PRE>") and (t[-6:] == "</PRE>"):
		return TRUE
	else:
		return FALSE

def wrapLines (
	s,		# the string to wrap.  can contain multiple lines, with
			# line breaks delimited by LF (defined below)
	maxlen		# integer; desired maximum line length
	):
	# Purpose: wrap lines of text in "s" so that each has length less than
	#	or equal to "maxlen", where possible
	# Returns: string containing the wrapped lines.  Individual lines are
	#	delimited by LF
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes: We do not guarantee that all the output lines are <= "maxlen"
	#	characters.  This is because wrapLines() does intelligent
	#	wrapping -- it wraps at word boundaries (defined by a space).
	#	If a line has no spaces before length "maxlen", we do not
	#	attempt to wrap it.
	# Example:
	#	s = "Here is a simple\nexample of a wrapped line.\n"
	#	wrapLines (s, 10) returns:
	#	    "Here is a \nsimple\nexample \nof a \nwrapped \nline.\n"

	LF = '\n'
	line_list = []				# list of generated lines
	lines = string.split (s, LF)		# list of input lines

	for line in lines:
		done = (len (line) <= maxlen)	# done splitting this line?
		while not done:
			# get "p", the position after the final space in the
			# first maxlen characters of "line".

			p = 1 + string.rfind (line [:maxlen], ' ')
			if p == 0:
				done = TRUE	# no spaces in line
			else:
				line_list.append (line [:p])
				line = line [p:]
				done = (len (line) <= maxlen)
		line_list.append (line)
	return string.join (line_list, LF)

def splitList (
	items,		# the list of items to split
	n		# the maximum number of items per sublist
	):
	# Purpose: splits "items" in a list of sub-lists, each of which has
	#	"n" or fewer items in it
	# Returns: list of lists as described in Purpose
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Example:
	#	splitList ( [ 'a', 'b', 'c', 'd', 'e' ], 2)
	#		will return:
	#	[ ['a', 'b'], ['c', 'd'], ['e'] ]

	if len (items) < n:
		return [ items ]
	else:
		return [ items [:n] ] + splitList (items [n:], n)
