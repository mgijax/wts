#!/usr/local/bin/python

# script for altering CV tables within the WTS database (could be used
# elsewhere if needed, with few modifications)

# Note that this script is intended as a private script for whomever
# administers the database table contents (CV tables specifically), as no
# record locking is done.

import os
import sys
import cgi
import string

import Configuration
import regsub
import wtslib
import screenlib

tables = [ 'CV_Staff',
	'CV_WTS_Area',
	'CV_WTS_Size',
	'CV_WTS_Type',
	'CV_WTS_Status',
	'CV_WTS_Priority',
	'WTS_Template',
	'WTS_FieldType',
	'WTS_Help',
	]
tables.sort()

header = [
	'Content-type: text/html',
	'',
	'<HTML><BODY>',
	'<H2>%s: CV Editor</H2>' % Configuration.config['PREFIX'],
	]

footer = [ '</BODY></HTML>' ]

###--- Functions ---###

def openingPage ():
	list = [
		'<FORM ACTION=table_edit.cgi>',
		'Please select a table:',
		'<SELECT NAME=table>',
		]
	for tbl in tables:
		list.append ('<OPTION> %s' % tbl)
	list = list + [
		'</SELECT>',
		'<INPUT TYPE=submit NAME=submit VALUE=submit>',
		'</FORM>',
		]
	return string.join (header + list + footer, '\n')

def getKeyname (table):
	return '%s_key' % table[string.rfind(table, '_'):]

def orderedKeys (keys, keyname):
	tkeys = keys[:]
	tkeys.sort()
	if keyname in tkeys:
		tkeys.remove (keyname)
		tkeys.insert (0, keyname)
	return tkeys

def tablePage (table):
	link = '<A HREF="table_edit.cgi?table=%s&key=%s">%s</A>' % \
		(table, '%s', '%s')

	results = wtslib.sql ('select * from %s' % table)
	list = [ '<FORM ACTION=table_edit.cgi>' ]
	if not results:
		list.append( 'Table %s is empty' % table)
	else:
		list.append('Select a record from table %s' % table)
		keyname = getKeyname (table)
		tkeys = orderedKeys (results[0].keys(), keyname)

		list.append ('<TABLE border=1>')

		list.append ('<TR>')
		for key in tkeys:
			list.append ('<TH>%s</TH>' % key)
		list.append ('</TR>')

		for row in results:
			list.append ('<TR>')
			for key in tkeys:
				if key == keyname:
					value = link % (row[key], row[key])
				else:
					value = cgi.escape(str(row[key]))
				list.append ('<TD>%s</TD>' % value)
			list.append ('</TR>')
		list.append ('</TABLE>')
	list.append ('<INPUT TYPE=hidden NAME=table VALUE=%s>' % table)
	list.append ('<P>Or choose to <INPUT TYPE=submit VALUE=add NAME=add>')
	list.append (' a new record.')
	return string.join (header + list + footer, '\n')

def noneTrapped (s):
	if s is None:
		return ''
	return s

def field (name, value, readonly = 0):
	newname = '<DT><B>%s</B>' % name
	if readonly:
		value = '<DD>%s' % value
	else:
		value = '<DD><TEXTAREA ROWS=5 COLS=70 NAME="%s">%s</TEXTAREA>' \
			% (name, noneTrapped(value))
	return newname + value

def entryPage (table, key):
	keyname = getKeyname(table)
	row = wtslib.sql ('select * from %s where %s = %s' % (table, keyname,
		key))[0]
	tkeys = orderedKeys (row.keys(), keyname)

	list = [
		'Editing %s' % table,
		'<FORM ACTION=table_edit.cgi>',
		'<INPUT TYPE=hidden NAME="%s" VALUE=%s>' % (keyname, key),
		'<INPUT TYPE=hidden NAME=table VALUE=%s>' % table,
		'<INPUT TYPE=hidden NAME=op VALUE=edit>',
		'<DL>',
		field (keyname, key, 1),
		]
	for name in tkeys:
		if name != keyname:
			list.append (field (name, row[name]))
	list = list + [
		'</DL>',
		'<INPUT TYPE=submit NAME=save VALUE=save>',
		'</FORM>',
		]
	return string.join (header + list + footer, '\n')
	
def newEntry (table):
	keyname = getKeyname(table)
	row = wtslib.sql ('''select *
				from %s
				where %s = (select max(%s) from %s)''' % \
				(table, keyname, keyname, table))[0]
	tkeys = orderedKeys (row.keys(), keyname)

	key = row[keyname] + 1
	list = [
		'Adding to %s' % table,
		'<FORM ACTION=table_edit.cgi>',
		'<INPUT TYPE=hidden NAME=%s VALUE=%s>' % (keyname, key),
		'<INPUT TYPE=hidden NAME=table VALUE=%s>' % table,
		'<INPUT TYPE=hidden NAME=op VALUE=new>',
		'<DL>',
		field (keyname, key, 1),
		]
	for name in tkeys:
		if name != keyname:
			list.append (field (name, ''))
	list = list + [
		'</DL>',
		'<INPUT TYPE=submit NAME=save VALUE=save>',
		'</FORM>',
		]
	return string.join (header + list + footer, '\n')
	
def isInt (s):
	try:
		i = string.atoi(str(s))
		return 1
	except ValueError:
		return 0

def doubleQuote (s):
	return regsub.gsub ('"', '""', s)

def toUnderline (s):
	return regsub.gsub (' ', '_', s)

def toSpace (s):
	return regsub.gsub ('_', ' ', s)

def savedEntry (parms):
	table = parms['table']
	keyname = getKeyname(table)
	row = wtslib.sql (['set rowcount 1', 'select * from %s' % table])[1][0]
	tkeys = orderedKeys (row.keys(), keyname)
	if parms['op'] == 'new':
		s = 'insert %s (%s) values (%s)' % ( \
			table, string.join(tkeys, ', '), '%s')
		t = []
		for tk in tkeys:
			if not parms.has_key (toSpace(tk)):
				t.append ('null')
			elif isInt(row[tk]):
				t.append (parms[toSpace(tk)])
			else:
				t.append ('"%s"' % \
					doubleQuote(parms[toSpace(tk)]))
		s = s % string.join (t, ', ')
	else:
		s = 'update %s set %s where %s' % ( \
			table, '%s', '%s = %s' % (keyname, \
				parms[toSpace(keyname)]))
		t = []
		for tk in tkeys:
			if tk == keyname:
				continue
			if parms.has_key (toSpace(tk)):
				value = parms[toSpace(tk)]
			else:
				value = None
			if value is None:
				t.append ('%s = null' % tk)
			elif isInt(row[tk]):
				t.append ('%s = %s' % (tk, value))
			else:
				t.append ('%s = "%s"' % (tk, \
					doubleQuote(value)))
		s = s % string.join(t, ', ')
	wtslib.sql (s)
	list = [
		'saved!',
		]
	return string.join (header + list + footer, '\n')
	
###--- Main Program ---###

try:
	form = cgi.FieldStorage()			# input from GET/POST
	parms = wtslib.FieldStorage_to_Dict(form)	# convert to {}
	if parms.has_key('submit'):
		del parms['submit']
	if len(parms) == 0:
		print openingPage()			# choose page
	elif len(parms) == 1:
		tbl = parms['table']
		print tablePage (tbl)			# choose record
	else:
		tbl = parms['table']
		if parms.has_key ('add'):
			print newEntry (tbl)		# add record
		elif parms.has_key ('save'):
			print savedEntry (parms)	# save record
		else:
			key = parms['key']
			print entryPage (tbl, key)	# edit record
except:
	screenlib.gen_Exception_Screen ('table_edit.cgi')

###--- End of table_edit.cgi ---###
