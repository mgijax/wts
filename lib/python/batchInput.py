# Name: batchInput.py
# Purpose: provide the ability to do batch input through the WTS command line

import os
import sys
import types
import string
import regex
import regsub
import Configuration
import TabFile
import Set
import TrackRec
import wtslib

LF = '\n'

def log_error (
	line,	# string; the line which caused the problem
	errors	# string or list of strings; error messages
	):
	# Purpose: send a dated error message with "line" and "errors" out to
	#	stderr
	# Returns: nothing
	# Assumes: stderr is available for writing
	# Effects: writes to stderr
	# Throws: nothing

	sys.stderr.write (wtslib.current_Time () + LF)
	sys.stderr.write (str (line) + LF)
	if type (errors) != types.ListType:
		errors = [ errors ]
	for err in errors:
		sys.stderr.write (err + LF)
	sys.stderr.write (LF)
	return

def batchInput (
	filename	# string; name of the tab-delimited file to input
	):
	# Purpose: read filename, parse, and make needed changes to TRs
	# Returns: integer number of errors found
	# Assumes: 1. current user has permission to read "filename"; 
	#	2. db's SQL routines have been initialized
	# Effects: reads the file and updates the tracking record tables as
	#	needed in the WTS database
	# Throws: 1. propagates wtslib.sqlError if there are problems updating
	#	the database; 2. propagates IOError if there are problems
	#	reading "filename"

	tdf = TabFile.TabFile (filename)
	for row in tdf.getList ():
		try:
			tr_nr = row ['TR Nr']
			tr = TrackRec.TrackRec (string.atoi (tr_nr))
		except ValueError, KeyError:
			log_error (tdf.getLine (row), \
				'Cannot parse value for TR number, ' + \
				'or cannot load the specified TR')
			continue

		rowKeys = Set.Set ()
		for k in row.keys ():
			rowKeys.add (k)
		rowKeys.remove ('TR Nr')	# already handled this one
		rowKeys.remove ('Directory')	# managed by system
		rowKeys.remove ('Project Definition')	# excluded by spec
		rowKeys.remove ('Progress Notes')	# excluded by spec

		plusMinus = regex.compile ('[+-]')
		for k in rowKeys.values ():
			if row[k] == '':
				pass
			elif k in TrackRec.SINGLE_VALUED_CV:
				value = regsub.gsub ('[+-]', '', row[k])
				tr.set_Values ({k : value})
			elif k in TrackRec.MULTI_VALUED:
				old_value = tr.dict ()[k]
				if plusMinus.search (row[k]) == -1:
					tr.set_Values ({k : row[k]})
				else:
					changes = regsub.split (row[k], ' *, *')
					for c in changes:
						if c[0] == '+':
							tr.addToCV (k, c[1:])
						elif c[0] == '-':
							tr.removeFromCV (k,
								c[1:])
						else:
							log_error (tdf.getLine (
								row),
								'Missing +/- '
								' in %s' % k)
			else:
				tr.set_Values ({k : row[k]})
		try:
			vals = TrackRec.validate_TrackRec_Entry (tr.dict ())
			tr.set_Values (vals)
			tr.lock ()
			tr.save ()
		except TrackRec.alreadyLocked, wtslib.sqlError:
			log_error (tdf.getLine (row), sys.exc_value)
		except IndexError:
			log_error (tdf.getLine (row),
				"Could not find TR in database")
		except:
			log_error (tdf.getLine (row),
				wtslib.string_To_List (sys.exc_value,
				TrackRec.error_separator))
		try:
			tr.unlock ()
		except TrackRec.notLocked:
			pass
