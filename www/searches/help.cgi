#!/usr/local/bin/python

# Help-file generating script for WTS

# Depends on a table WTS_Help with columns _Help_key, fieldname, description,
# toQuery, and cvName.

import os
import sys
import cgi
import string

import Configuration
import wtslib
import screenlib
import TrackRec
import HTMLgen

###--- Functions ---###

def getPage (
	req		# string; field to get help on, should be one of the
			#	keys in TrackRec.NAME_TO_DB
	):
	# Purpose: compose and return the screenlib.Help_Screen object for
	#	the given 'req'
	# Returns: screenlib.Help_Screen object
	# Assumes: we can query the database
	# Effects: queries the database
	# Throws: propagates any exceptions raised by wtslib.sql()

	page = screenlib.Help_Screen()		# blank page

	results = wtslib.sql ('''select *
				from WTS_Help
				where fieldname = '%s' ''' % req)

	fieldname = results[0]['fieldname']
	description = results[0]['description']
	toQuery = results[0]['toquery']
	cvName = results[0]['cvname']

	page.setup (fieldname, description, toQuery, cvName)
	return page

###--- Main Program ---###

try:
	form = cgi.FieldStorage()			# input from GET/POST
	parms = wtslib.FieldStorage_to_Dict(form)	# convert to {}

	req = string.strip (parms['req'])		# get the request
	page = getPage (req)				# build the page
	page.write ()					# and send it out
except:
	screenlib.gen_Exception_Screen ('help.cgi')

###--- End of help.cgi ---###
