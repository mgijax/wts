# Name: Template.py
# Purpose: contains classes, functions, and global variables used to work with
#	the text field templates within WTS
# Notes: assumes that the WTS database has the following tables:
#	WTS_Template
#		_Template_key (int)
#		_FieldType_key (int)	-- foreign key to WTS_FieldType
#		name (varchar)
#		value (text)		-- contains no " characters
#	WTS_FieldType
#		_FieldType_key (int)
#		name (varchar)		-- contains no " characters

import sys
if '.' not in sys.path:
	sys.path.insert (0, '.')
import os

import string		# standard Python libraries
import regsub

import Configuration	# WTS libraries
import wtslib

# list of substitutions to be made to the value of each template -- each list
# element is a tuple containing the regex to find and the string with which
# to replace it

substitutions = [
	('\.user\.',	os.environ['REMOTE_USER']),
	]

def expand (
	s		# string; value of the template (raw from the db)
	):
	# Purpose: process all the standard 'substitutions' to 's'
	# Returns: string; 's' after the substitutions have been made
	# Assumes: nothing
	# Effects: nothing
	# Throws: propagates any exception raised by regsub.gsub

	for (exp, st) in substitutions:
		s = regsub.gsub (exp, st, s)
	return s

class TemplateSet:
	# IS:	a set of Template objects
	# HAS:	zero or more Template objects
	# DOES: provides methods to represent the set as a Javascript array
	#	or as an HTML select box

	def __init__ (self,
		fieldType	# string; name of the text field type
		):
		# Purpose: load data from the database and populate this set
		#	of Template objects
		# Returns: nothing
		# Assumes: wtslib.sql can access the database
		# Effects: queries the database
		# Throws: propagates any exceptions raised by wtslib.sql


		self.set = []
		rows = wtslib.sql ('''
				select t._Template_key, t.name, t.value
				from WTS_Template t, WTS_FieldType f
				where t._FieldType_key = f._FieldType_key
					and f.name = "%s"
				order by t._Template_key
				''' % fieldType)
		for row in rows:
			self.set.append (Template(row))
		return

	def __len__ (self):
		# Purpose: return the number of templates in this set
		# Returns: integer
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return len(self.set)

	def getJavascript (self,
		arrayname	# string; what do you want to name the array?
		):
		# Purpose: builds a string of Javascript which represents the
		#	keys and template values
		# Returns: string described above
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		# find the highest key that is defined in the set of templates

		maxkey = 0
		if len(self.set) > 0:
			maxkey = self.set[-1].getKey()

		# start with all blank strings up to that key

		dict = {}
		for i in range(0, maxkey + 1):
			dict[i] = ''

		# fill in non-blank strings where defined

		for template in self.set:
			dict[template.getKey()] = template.getValue()

		# now build the Javascript array from the strings in dict

		items = []
		for i in range(0, maxkey + 1):
			items.append ('"%s"' % dict[i])

		jscript = [ '%s = new Array (' % arrayname,
			string.join (items, ', '),
			')'
			]
		
		return string.join (jscript, '\n')

	def getSelect (self,
		fieldname	# string; what do you want the Select named?
		):
		# Purpose: build a string which represents the keys and
		#	template names as an HTML SELECT box
		# Returns: string described above
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		pairs = []
		for template in self.set:
			pairs.append ( (template.getName(), \
				template.getKey()) )
		pairs.sort()

		html = [ '<SELECT NAME="%s">' % fieldname ]
		for (name, key) in pairs:
			html.append ('<OPTION VALUE="%s"> %s' % (key, name))
		html.append ('</SELECT>')

		return string.join (html, '\n')

## END TemplateSet

class Template:
	# IS:	one "template" that the user can use in working with WTS
	#	text fields
	# HAS:	a key, a name, and a value (the actual template)
	# DOES:	has accessor methods

	def __init__ (self,
		row		# dictionary; one row from WTS_Template
		):
		# Purpose: instantiates 'self'
		# Returns: nothing
		# Assumes: row contains keys _Template_key, name, and value
		# Effects: nothing
		# Throws: nothing

		self.key = row['_Template_key']
		self.name = row['name']
		self.value = expand (row['value'])
		return

	def getKey (self):
		# Purpose: accessor method
		# Returns: integer key
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.key

	def getName (self):
		# Purpose: accessor method
		# Returns: string name of the template
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.name

	def getValue (self):
		# Purpose: accessor method
		# Returns: string value of the template
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing

		return self.value

## END Template
