#!/usr/local/bin/python

# Name: TabFile.py
# Purpose: provide a mechanism for working with a tab-delimited file as a
#	means of batched i/o for WTS.

import copy
import string
import regex
import regsub

TAB = '\t'
LF = '\n'

# If there is a special field that should appear first in the file, it
# can appear in this FIRST_FIELD list.  Occurrences of items in FIRST_FIELD
# will all be converted to use the first item in FIRST_FIELD.

# If using this for another app, feel free to replace this variable...
#	TabFile.FIRST_FIELD = [ ... ])

# Since we're only dealing with tracking records, we start with these: 

FIRST_FIELD = [ 'TR Nr', 'tr nr', 'tr', 'TR', 'TR #', 'tr #']


def dictToString (
	dict		# the dictionary to be converted to a string
	):
	# Purpose: convert 'dict' to a string
	# Returns: a string with the concatenation of fields of 'dict'
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes: Since dictionaries guarantee no particular key ordering, we
	#	cannot depend on a particular value of str(dict).  This makes
	#	it difficult to use a dictionary as a key for another
	#	dictionary.  This function can be used to build a string
	#	identifier for a dictionary, but it should only be depended
	#	on for the purposes of this TabFile.

	s = ''
	key_list = dict.keys ()
	key_list.sort ()
	for key in key_list:
		s = s + str(dict[key])
	return s


class TabFile:
	# Concept:
	#	IS: an abstraction of a tab-delimited file
	#	HAS: a list of dictionaries, each of which represents a row of
	#		data in the tab-delimited file; a dictionary of data
	#		lines, indexed by data dictionary
	#	DOES: reads & parses a TDF, saves a TDF, returns as a string
	#		representation, returns a data line for a data
	#		dictionary, etc.
	# Methods:
	#	__init__ (optional filename)
	#	setList (list of data dictionaries)
	#	getList ()
	#	getLine (data dict for one record)
	#	__str__ ()
	#	save (filename)
	#	read (filename)

	def __init__ (self,
		filename = None		# if non-None, we read the file
		):
		# Purpose: initialize a new TabFile object, and optionally read
		#	a data file at initialization
		# Returns: nothing
		# Assumes: if it is not None, "filename" specifies a file
		#	readable by the current user
		# Effects: if "filename" is not None, it reads that file from
		#	the file system
		# Throws: IOError if the specified "filename" cannot be read

		self.data = []		# list of {}, one per data record
		self.dataLines = {}	# maps from data dictionary to data line
		if filename is not None:
			self.read (filename)
		return

	def setList (self,
		dataList	# list of dictionaries, each of which should
		):		# have the same keys and represent a single row
				# of data
		# Purpose: set the contents of this TabFile object
		# Returns: nothing
		# Assumes: that dataList is well-formed
		# Effects: see Purpose
		# Throws: nothing
	
		self.data = dataList
		return

	def getList (self):
		# Purpose: get a copy of the data included in this TabFile
		# Returns: a list of dictionaries, each of which has the same
		#	keys and represents a single row of data
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return copy.deepcopy (self.data)

	def getLine (self,
		dict		# dictionary of values for which we want the
		):		# original data line
		# Purpose: retrieve the original data line corresponding to the
		#	given data dictionary, "dict"
		# Returns: a string data line
		# Assumes: "dict" has not been altered since it was produced in
		#	the read() method
		# Effects: nothing
		# Throws: KeyError if "dict" has been altered

		try:
			return self.dataLines [dictToString(dict)]
		except:
			return 'Original line not found'

	def __str__ (self):
		# Purpose: return string representing this TabFile object as a
		#	tab-delimited file
		# Returns: a string
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing
		# Notes: The first line in the returned string is a header line
		#	with the (tab-delimited) filenames.  After the header
		#	is one line for each data row, with field values lined
		#	up below their respective fieldnames.  We should also
		#	note that if a 'TR Nr' field exists, it will always
		#	appear in the leftmost column.

		s = ''
		if len (self.data) > 0:
			kys = self.data[0].keys ()
			kys.sort ()

			# look through fields which should appear first in the
			# output.  If they exist, move them to the front of the
			# list of keys.

			for item in FIRST_FIELD:
				if item in kys:
					kys.remove (item)
					kys.insert (0, FIRST_FIELD[0])

			# build the header line, and add it to "s"

			line = ''
			for item in kys:
				line = line + item + TAB
			s = line [:-1] + LF

			# now, build each data line and add them to "s"

			for row in self.data:
				line = ''
				for item in kys:
					line = line + str (row [item]) + TAB
				s = s + line[:-1] + LF
		return s

	def save (self,
		filename	# name of file to which to write this data
		):
		# Purpose: writes the data from this TabFile object as a tab-
		#	delimited file to the given "filename"
		# Returns: nothing
		# Assumes: user has write permission in the necessary directory
		# Effects: creates (or overwrites) the specified file
		# Throws: IOError if the user cannot write the file
		# Notes: file format matches that defined in __str__()

		fp = open (filename, 'w')
		fp.write (str (self))
		fp.close ()
		return

	def read (self,
		filename	# name of the file from which we should read
		):		# the data for this TabFile object
		# Purpose: get the data from "filename" and store it in "self"
		# Returns: nothing
		# Assumes: format of file specified by "filename" is
		#	correct
		# Effects: reads the specified file and stores data in "self"
		# Throws: 1. IOError if the file cannot be read,
		#	2. TabFile.BadFileFormat if we have problems parsing
		#	the data
		# Notes: The file format is that specified in __str__(), but
		#	with a couple of  additions:  1. if the first field is
		#	TR Nr, then there can be a comma-separated list of TR
		#	numbers -- this should be expanded into separate data
		#	lines.  2. A '#' at the start denotes a comment line,
		#	which should be ignored.

		self.data = []
		self.dataLines = {}

		fp = open (filename, 'r')
		lines = fp.readlines ()
		fp.close ()

		temp_lines = lines[:]
		lines = []
		for line in temp_lines:
			if regex.match ('[ \t]*#', line) == -1:
				lines.append (line)

		if len (lines) > 0:
			fieldnames = string.split (string.strip (lines[0]), TAB)
			if fieldnames[0] in FIRST_FIELD:
				fieldnames[0] = FIRST_FIELD[0]
			fieldIndices = range (0, len (fieldnames))

			# note that we need to use regsub.split() here rather
			# than string.split() because we need to handle empty
			# field values

			for line in lines[1:]:
				original_line = string.rstrip (line)
				line = string.strip (line)
				if len (line) == 0:		# skip blanks
					continue
				fields = regsub.split (line, TAB)
				fieldCount = len(fields)

				# now, for the special "first field", we need to
				# allow a comma-separated list of values for
				# which we need to replicate this row

				if fieldnames[0] in FIRST_FIELD:
					vals = regsub.split (fields[0], ' *, *')
				else:
					vals = [fields [0]]
				for val in vals:
					dict = {}
					fields [0] = val
					for i in fieldIndices:
						if i < fieldCount:
							dict[fieldnames[i]] = \
								fields[i]
						else:
							dict[fieldnames[i]] = ''
					self.data.append (dict)
					self.dataLines [dictToString(dict)] = \
						original_line
		return
