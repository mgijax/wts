#!/usr/local/bin/python

# Name: Template_File.py
# Purpose: implements the Template_File class for WTS, a class which provides a
#	simple mechanism for writing a dictionary of fieldname -> value pairs
#	out to an HTML-formatted external file, and then reading them back
#	in again.

import os
import copy
import regex
import string
import HTMLgen

# Global variables (treat as constants) which are used to delimit fieldnames

FIELD_START = ':__'		# delimits the start of a field name
FIELD_STOP = '__:'		# delimits the end of a field name


class Template_File:
	# Concept:
	#	IS: an HTML-formatted text-file representation of a dictionary
	#	HAS: a dictionary of fieldnames and values, an list of those
	#		fieldnames in the order they should be written to a
	#		file, and the name of the file to be read/written
	#	DOES: Methods are provided so one may save or load a dictionary
	#		to (or from) an HTML-formatted file, erase that file,
	#		and return the current dictionary in the Template_File
	#		object.
	# Implementation:
	#	File Format:	The file produced/read consists of pairs of
	#		fieldnames and values.  Each fieldname are delimited
	#		with the above-defined FIELD_START and FIELD_STOP
	#		strings, and will appear as the first non-blank part of
	#		a line.  The value will begin after the FIELD_STOP
	#		string and is considered to continue until the next
	#		fieldname is found (complete with the delimiters).
	#		Leading and trailing spaces are stripped from the
	#		values.  For readability, a paragraph marker is used to
	#		separate each field-value pair from the next one.
	#	Methods:
	#		__init__ (filename, optional dictionary, optional
	#			ordered list of keys)
	#		dict ()
	#		getFilename ()
	#		load ()
	#		save ()
	#		erase ()
	#		set_Key_Order (list of fieldnames (in order))

	def __init__ (self,
		filename,	# string; name of the file to use in saving /
				# loading this template file
		mapping={},	# dictionary of fieldnames (keys) and their
				# associated values to put in the file (may be
				# {} if we're just going to read in a file)
		key_order=None	# list specifying the keys of mapping, in the
				# order you'd like them to appear in the file
				# produced.  (if None, we write all of them
				# alphabetically)
		):
		# Purpose: create and initialize a new Template_File object
		# Returns: nothing
		# Assumes: "filename" is valid
		# Effects: see Purpose
		# Throws: nothing
		# Notes: If "mapping" is not empty and "key_order" is None, then
		#	we define "key_order" to be the sorted (alphabetically)
		#	list of keys of "mapping".

		# store the parameters in the object itself

		self.dictionary = mapping	# dictionary which maps
						# fieldname to field value

		self.filename = filename	# string name of the template
						# file (in the file system)

		# self.key_order is a list of the keys in self.dictionary, in
		# the order they would be saved to a file in the file system.

		if key_order:
			self.key_order = key_order
		else:
			self.key_order = self.dictionary.keys ()
		return


	def dict (self):
		# Purpose: get a copy of the dictionary of fieldnames & values
		# Returns: a copy of the dictionary of fieldnames and values
		#	represented by this Template_File
		# Assumes: nothing
		# Effects: see Purpose.  (That dictionary is initialized in the
		#	"__init__()" method and updated by the "load()" method.)
		# Throws: nothing

		return copy.deepcopy (self.dictionary)


	def getFilename (self):
		# Purpose: return the filename of this template file
		# Returns: returns the name of the file for this template file
		#	in the file system
		# Assumes: nothing
		# Effects: see Returns
		# Throws: nothing

		return self.filename


	def load (self):
		# Purpose: read, parse, and store fieldnames and values from
		#	the stored filename
		# Returns: nothing
		# Assumes: nothing
		# Effects: Resets this object's data dictionary to be empty,
		#	then reads the given file (self.filename), parses out
		#	fieldname -> value pairs, and stores them in this
		#	object's data dictionary.  Sets the objects "key_order"
		#	to match the order in which the fieldnames appeared in
		#	the file.
		# Throws: propagates the standard Python IOError if we cannot
		#	open for reading the file given in self.filename
		# Notes: See class header comments for the file format.

		global FIELD_START, FIELD_STOP

		self.dictionary = {}	# the object's dictionary of data
		self.key_order = []	# ordering of fieldnames in the file
		field = None		# fieldname currently being read
		start = None		# line number on which data starts

		# open the file and read the lines into a list (named lines)

		fp = open (self.filename, "r")
		lines = fp.readlines ()
		fp.close ()

		# compile a regular expression (re) which will match lines in
		# the standard format and extract the fieldname and value.
		# Standard format is:
		#	:__fieldname__: data for that field
		#		(can span multiple lines)
		#	:__new_fieldname__: data for this field
		# fieldnames can be comprised of letters, digits, spaces, 
		# underscores, and pound signs

		re = regex.compile (
			'[ \t]*'		# ignore initial spaces & tabs
			':__'			# fieldname left delimiter
			'\([A-Za-z0-9_# ]+\)'	# group1 = fieldname
			'__:'			# fieldname right delimiter
			'[ \t]*'		# ignore spaces & tabs before...
			'\(.*\)'		# group2 = rest of line
			)

		# now, we need to go through the lines until we find the first
		# one that matches re.  (This is to skip over all the HTML
		# header stuff)

		for i in range (0, len (lines)):
			if re.match (lines [i]) >= 0:
				start = i	# note the index of the first...
				break		# data line, then stop the loop

		# if start is non-None, then we found the first data line.  Go
		# through the lines from that point onward and collect
		# fieldnames and values.

		if start:
			for line in lines [start:]:

				# if we match the regular expression, then we
				# are beginning a new field-value pair.  Note
				# the field name and start the value (with a
				# newline added, since this would not have been
				# captured by "re").  Also add this field to
				# the "key_order".

				if re.match (line) >= 0:
					field = re.group (1)
					self.key_order.append (field)
					self.dictionary [field] = \
						re.group (2) + '\n'

				# if "re" didn't match, then we should interpret
				# this line as a continuation of the value for
				# the current field.  (allowing multi-line
				# values)  Just concatenate this new line to
				# that value.

				else:
					self.dictionary [field] = \
						self.dictionary [field] + line

			# having processed all the lines, we now need to clean
			# up a few details such as...

			# The final field that we found should have final HTML
			# tags for the file.  So, we need to clip that value if
			# we find the terminal tags: </BODY></HTML>.

			value = string.rstrip (self.dictionary [field])

			if (string.upper (value [-7:]) == '</HTML>'):
				value = string.rstrip (value [:-7])

			if (string.upper (value [-7:]) == '</BODY>'):
				value = string.rstrip (value [:-7])

			self.dictionary [field] = value

			# In generating the file, we also included an
			# intermediary paragraph marker for spacing between
			# fields.  This paragraph marker would have been
			# collected with the field values.  So, now we can go
			# through each value and strip the trailing <P> from
			# each.  At the same time, let's strip any whitespace
			# from the end of each field value.

			for k in self.dictionary.keys ():

				# first, let's strip the extraneous whitespace
				# at the end of the field value:

				self.dictionary [k] = string.rstrip (
					self.dictionary [k])

				# Now, look for a paragraph marker at the end
				# of the field value.  If it is there, remove
				# it, and remove any whitespace before it.
				# Then, repeat.

				while (self.dictionary [k][-3:] in
					['<P>', '<p>']):
					self.dictionary [k] = string.rstrip (
						self.dictionary [k][:-3])

		# no else clause -- if we didn't find any data lines, then we
		# can just return with an empty dictionary and key_order.

		return


	def save (self):
		# Purpose: save the fieldnames and values in this object's
		#	current data dictionary to be HTML-formatted in the
		#	stored filename
		# Returns: nothing
		# Assumes: user has write permission on the current directory,
		#	or the directory included in self.filename
		# Effects: creates an HTML-formatted text file with the given
		#	filename (self.filename), containing the fieldnames and
		#	values from the current dictionary
		# Throws: nothing
		# Notes: see the class comments for the file format

		global FIELD_START, FIELD_STOP

		# do the initial HTML setup

		doc = HTMLgen.SimpleDocument (title = 'WTS External File: ' + \
			self.filename)

		# for each item in the dictionary...

		actual_fields = self.dictionary.keys ()
		for key in self.key_order:
			if key in actual_fields:

			# send out a delimited key followed by '  '
			# followed by the value and a trailing paragraph marker

				value = str (self.dictionary [key])
				doc.append (HTMLgen.RawText (FIELD_START + \
					key + FIELD_STOP + '  ' + value))

				doc.append (HTMLgen.P())

		# write out the document, then delete the object

		doc.write (self.filename)
		del doc
		return


	def set_Key_Order (self,
		key_order	# list specifying the keys (fieldnames) in this
				# object's data dictionary, in the order you'd
				# like them to appear in the file produced.
		):
		# Purpose: sets the object's "self.key_order" to be that given
		#	by the parameter
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		self.key_order = key_order
		return


	def erase (self):
		# Purpose: erase file with the stored filename (self.filename)
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: propagates the posix.error exception if a file with
		#	self.filename does not exist

		os.remove (self.filename)

### End of Class: Template_File ###

#-SELF TESTING CODE---------------------------------------------------------

def self_test ():
	# Purpose: test the Template_File class
	# Returns: nothing
	# Assumes: current user has read/write permission in current directory
	# Effects: creates a Template_File object, saves it, loads it, and then
	#	compares the values to see that they match.
	# Throws: nothing

	dict = {	'TR #' : 'TR0003',	'Size' : 'small',
			'Status' : 'new',	'Status Date' : '1/1/98 1:03PM',
			'Description' : 'This is a simple test of the ' + \
				'template file mechanism.  We will save ' + \
				'several fields to a file and then read ' + \
				'them in.' }

	out_file = Template_File ('temp.html', dict)
	out_file.set_Key_Order ( ['TR #', 'Status', 'Status Date', 'Size',
		'Description' ])
	out_dict = out_file.dict ()
	out_file.save ()

	in_file = Template_File ('temp.html')
	in_file.load ()
	in_dict = in_file.dict ()

	in_file.erase ()

	diff = 0
	for k in out_dict.keys ():
		if out_dict[k] <> in_dict[k]:
			diff = 1
	for k in in_dict.keys ():
		if out_dict[k] <> in_dict[k]:
			diff = 1
	if (diff <> 0):
		print ('failed test - mismatch occurred')
	else:
		print ('successful test - matches confirmed')
	return


if __name__ == '__main__':		# if executed from command line,
	self_test()			# do a self test
