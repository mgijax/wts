#!/usr/local/bin/python

# Name: javascript.py
# Purpose: defines several string variables, each of which includes
#	Javascript code for use within WTS.
# Notes: To more easily identify strings from this module, they will all
#	be prepended with "js_"

	# Purpose: get an integer representation of the current time
	# Returns: an integer number of milliseconds that have elapsed since
	#	the epoch
	# Assumes: Javascript does garbage collection
	# Effects: nothing
	# Throws: nothing

js_millisecondsSinceEpoch = '''
	function millisecondsSinceEpoch () {
		now = new Date();
		return now.getTime();
	}
'''
	# Purpose: check the elapsed time since this function was last called
	# Returns: true if a specified minimum amount has been met, or false
	#	if not
	# Assumes: the millisecondsSinceEpoch() function is available in the
	#	same block of Javascript code.
	# Effects: nothing
	# Throws: nothing
	# Notes: You should use the % operator to fill in the %d in this string
	#	with the minimum number of milliseconds, and the %s with the
	#	message to pop up if not enough time has elapsed.
	# Example: Typical usage in Python, to cancel a second click of the
	#	submit button on a form:
	#
	#	print '<HTML><HEAD>'
	#	print '<SCRIPT LANGUAGE="JavaScript">'
	#	print '<!--'
	#	print javascript.js_millisecondsSinceEpoch
	#	print javascript.js_enoughTimeElapsed % (2000, \
	#		"Do not double-click form buttons")
	#	print '//-->'
	#	print '</HEAD><BODY>'
	#	print '''<FORM action="foo.cgi"
	#			onSubmit="return enoughTimeElapsed()">'''
	#	print ' ...rest of form... </BODY></HTML>'

js_enoughTimeElapsed = '''
	lastCalled = null;

	function enoughTimeElapsed () {
		if (lastCalled == null)
			result = true;
		else {
			if ((millisecondsSinceEpoch() - lastCalled) < %d) {
				window.alert ("%s")
				result = false;
			}
			else
				result = true;
		}
		lastCalled = millisecondsSinceEpoch ();
		return result;
	}
'''
