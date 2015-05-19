#!/usr/local/bin/python

# screenlib.py - implements classes to represent each HTML form in the WTS
#	web interface, along with wrapper functions for a selected few which
#	are often used.

'''
# Author:
#	Jon Beal
# Date written:
#	4-28-98		began initial implementation
# Summary:
#	implements one class for each HTML form in the WTS web interface.
#	uses HTMLgen module to do all HTML generation.  Each class uses a
#	setup function which takes a few data parameters.  Each also writes
#	its output to stdout.  For commonly used classes, a few wrapper
#	functions are provided.
# Requirements:
#	* a resource file for HTMLgen (by default named 'wts.rc' in the common
#	  directory) will provide default setup information for each page
#
#	* provide wrapper functions for commonly used classes
#
#	* provide a consistent interface to the creation of all WTS web pages
#
# Supporting Classes:
#	Button
#		__init__ (value, onClick)
#		__str__ ()
#	MetaList
#		__init__ (*HTMLgen.Meta objects)
#		__str__ ()
#		append (HTMLgen.Meta object)
#	WTS_Form (inherits from HTMLgen.Form)
#		__init__ (cgi script name, various keywords)
#		__str__ ()
#	WTS_Document (inherits from HTMLgen.SeriesDocument)
#		__init__ (various keywords)
#
# Screen Classes:  (all inherit from WTS_Document)
#	Error_Screen
#		setup (errors, opt. abort cgi name, opt. back count, opt. TR#)
#	Exception_Screen 
#		setup (exception type, exception value, traceback table)
#	GoTo_Screen
#		setup (url to load)
#	Message_Screen
#		setup (message, back count)
#	TrackRec_ShortForm_Screen
#		setup (new TrackRec object for form)
#	Password_Screen
#		setup (current user name)
#	New_TrackRec_Screen
#		setup ()
#	TR_Notification_Screen
#		setup (tracking record number)
#	TrackRec_Detail_Screen
#		setup (tracking record numbers, previous tr screen flag)
#	TrackRec_Edit_Screen
#		setup (tracking record)
#	Query_Result_Screen
#		setup (clean dictionary)
#	Status_Grid_Screen
#		setup (row_type, date_range, table object)
#
# Wrapper Functions:
#	gen_Exception_Screen (filename)
#	gen_Message_Screen (page title, message, back count)
'''

import os
import sys
import Configuration
import regsub
import traceback
import types
import HTMLgen
import string
import wtslib
import TrackRec
import Controlled_Vocab
import javascript


#--GLOBALS-----------------------------------------------------------------

RESOURCE_FILE = 'data/wts.rc'		# resource file
WTS_HOME_PAGE = '../index.html'
PREFIX = Configuration.config['PREFIX']

#--CLASSES-----------------------------------------------------------------

class Button:
	''' provides an HTMLgen-compatible "button" object which will execute
	#	Javascript when it is clicked
	#
	# Requires:	nothing
	# Effects:	see above
	# Modifies:	no side effects
	'''
	def __init__ (self, value, onClick):
		''' creates and initializes a Button object
		#
		# Assumes:	value and onClick are not None
		# Requires:	value - text string to appear on button
		#		onClick - Javascript code to execute when user
		#		clicks the button
		# Effects:	see above
		# Modifies:	no side effects, just initializes self
		'''
		self.value = value	# text string to appear on the button
		self.onClick = onClick	# string of Javascript which executes
					# when the button is clicked.

	def __str__ (self):
		''' returns a string of HTML text which represents the button
		#
		# Requires:	nothing
		# Effects:	see above
		# Modifies:	no side effects
		'''
		return "<INPUT TYPE=button VALUE='" + self.value + \
			"' onClick='" + self.onClick + "'>"

### End of Class: Button ###


class MetaList:
	# Concept:
	#	IS: an HTMLgen-compatible representation of a list of Meta tags
	#	HAS: zero or more HTMLgen.Meta objects
	#	DOES: collects tags and returns a string containing the
	#		concatenation of their string equivalents
	# Implementation:
	#	To ensure HTMLgen compatibility, we need to define __str__()
	#	and append() methods.

	def __init__ (self,
		*meta_objects	# zero or more HTMLgen.Meta objects
		):
		# Purpose: create a new MetaList object and add the given
		#	meta_objects to it
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		self.contents = []
		for m in meta_objects:
			self.append (m)
		return

	def __str__ (self):
		# Purpose: get a string representing the MetaList as HTML
		# Returns: a string (see Purpose)
		# Assumes: nothing
		# Effects: nothing
		# Throws: nothing
		
		s = ''
		for m in self.contents:
			s = s + str(m)
		return s

	def append (self,
		meta_object		# HTMLgen.Meta object to add
		):
		# Purpose: add the given "meta_object" to the list we are
		#	collecting
		# Returns: nothing
		# Assumes: nothing
		# Effects: adds to the list of this MetaList's "contents"
		# Throws: nothing

		self.contents.append (meta_object)
		return

### End of Class: MetaList ###


class WTS_Form (HTMLgen.Form):
	# Concept:
	#	IS: an HTMLgen-compatible representation of an HTML form.  It
	#	    inherits from HTMLgen.Form and extends it to allow:
	#		* zero or more Submit buttons on the form
	#		  (HTMLgen.Form allows at most one)
	#		* centered buttons at both top and bottom of the form
	#		  (HTMLgen.Form only has them at the top, and aligns
	#		  them to the left)
	#		* buttons other than Submit and Reset, based on the
	#		  above Button class (HTMLgen.Form only allows Submit
	#		  and Reset buttons)
	#		* either POST (the default) or GET submissions
	#		  (HTMLgen.Form has POST hard-coded)
	#	HAS: a string for what CGI to invoke upon a submit event, a
	#		list of HTMLgen objects which make up the contents of
	#		the form, a list of Button objects, a list of submit
	#		buttons, a string for the submission type, and an
	#		optional Reset button
	#	DOES: A WTS_Form serves as a container for collecting HTMLgen
	#		objects to appear on an HTML form.  Objects may be
	#		added using the append method.  The current HTML
	#		representation may be retrieved at any time using the
	#		__str__ method.
	# Implementation:
	#	A WTS_Form object has several attributes (instance variables):
	#
	#	* buttons - a Button object or list of Button objects which
	#		should appear at the top and bottom of the form (or
	#		None)
	#	* contents - list of HTMLgen compatible objects which should be
	#		displayed on this form, in the order they should be
	#		converted to HTML and written out
	#	* cgi - string containing the name of the CGI script to invoke
	#		when this form is submitted
	#	* submit - submit button or list of submit buttons to be placed
	#		at the top and bottom of the form (or None)
	#	* reset - reset button to be placed at the top and bottom of
	#		the form (or None)
	#	* target - standard target field as used in HTML forms (?) --
	#		not used by WTS, but retained to maintain compatibility
	#		with HTMLgen
	#	* enctype - type of encryption to be used when submitting this
	#		form
	#	* name - string name of the form (not for display, but to be
	#		in its HTML definition) -- not used by WTS, but
	#		retained to maintain compatibility with HTMLgen
	#	* onSubmit - string containing Javascript code to be executed
	#		on a submit event -- not used in WTS, but retained to
	#		maintain compatibility with HTMLgen
	#	* method - string specifying a "GET" or "POST" submission

	def __init__ (self,
		cgi = None,	# string filename specifying what CGI script to
				# invoke when this form is submitted (if we are
				# to call one)
		**kw		# keyword parameters may be used to set any of
				# the object attributes defined in the class
				# comments above (Implementation section)
		):
		# Purpose: initialize the WTS_Form object and handle keyword
		#	parameters to initialize its attributes (instance
		#	variables)
		# Returns: nothing
		# Assumes: values specified in keyword parameters are valid
		#	types for those attributes
		# Effects: Initializes the object's attributes to their default
		#	values and then overwrites any which are specified in
		#	the parameters to this __init__ method.
		# Throws: KeyError if a bad keyword is used in specifying a
		#	keyword parameter

		# initialize the object attributes (instance variables) which
		# are explained in the class comments above

		self.buttons = None	# new field - not in HTMLgen.Form
		self.method = "POST"	# new field - type of submission
		self.contents = []	#	/\
		self.cgi = cgi		#	||
		self.submit = None	#	||
		self.reset = None	# standard field in HTMLgen.Form
		self.target = None	#	||
		self.enctype = None	#	||
		self.name = None	#	||
		self.onSubmit = ''	#	\/

		# Now go through each of the keyword parameters specified.  If
		# an object attribute (instance variable) with that name exists,
		# then set it to the specified value.  If not, raise an
		# exception. (code copied from HTMLgen.Form)

		for item in kw.keys():
			if self.__dict__.has_key(item):
		 		self.__dict__[item] = kw[item]
			else:
				# using the standard exception KeyError to
				# denote a bad keyword parameter is the
				# mechanism used by HTMLgen.  Let's use it
				# here, too, to be consistent.

				raise KeyError, `item` + \
					' not a valid parameter of the ' + \
					'WTS_Form class.'
		return

	def __str__ (self):
		# Purpose: build and return a string of HTML-formatted text
		#	which represents this form
		# Returns: a string which includes HTML formatting tags to
		#	depict this form
		# Assumes: all objects on the form are HTMLgen compatible (they
		#	have a __str__ method which produces an HTML-formatted
		#	string to represent the object)
		# Effects: adds buttons to the top and bottom of the form's
		#	contents, then returns the string of HTML-formatted
		#	text produced by concatenating the HTML representations
		#	of each HTMLgen-compatible object in the form.  Note
		#	that this alters self.contents, so only call it once
		#	and only after you have finished producing the form.
		# Throws: nothing
		# Notes: This is a modified version of HTMLgen.Form's __str__
		#	method.  Changes were made to facilitate the WTS-
		#	specific formatting mentioned in the class comments
		#	above.  Again, note that this alters self.contents, so
		#	only call it once and only after you have finished
		#	producing the form.  We also have added code to handle
		#	the submission type definition in self.method.

		button_counter = 0	# how many buttons have been added
					# to the top of the form?  We need this
					# so that we can add buttons in the same
					# order to the top and the bottom of
					# the form.  (The prior is an insert
					# operation, while the latter is an
					# append operation.)

		# if there is at least one special submit button defined, then
		# we need to add it/them.  If there is not one, then skip it.

		if self.submit is not None:

			# get a list of submit buttons to be added to the form.
			# convert a single submit button to be a list of submit
			# buttons with just a single item, so we can use the
			# same code for adding a single button that we do for
			# a list of them.

			if type (self.submit) <> types.ListType:
				submit_list = [ self.submit ]
			else:
				submit_list = self.submit

			# now, go through each submit button (btn) in the list

			for btn in submit_list:

				# add the special submit button to the top 
				# and bottom of the form.  Inserting at the
				# button_counter position ensures that the
				# buttons at the top of the form are in the
				# same order as those at the bottom.

				self.contents.insert (button_counter, btn)
				self.contents.append (btn)

				# note that we have one more button in the
				# row of buttons at the top (and bottom) of
				# the form.  Remember, this is used so that we
				# know where to insert the next button at the
				# top of the form.

				button_counter = button_counter + 1

		# if any other buttons are defined, then add them after the
		# submit button (at the top and bottom of the form).

		if self.buttons <> None:

			# get a list of buttons to be added to the form.  If
			# there is only a single button, then put it into a
			# single-item list.

			if type (self.buttons) == types.ListType:
				button_list = self.buttons
			else:
				button_list = [ self.buttons ]

			for btn in button_list:

				# add the button (btn) to the top and bottom of
				# the form.  Inserting at the button_counter
				# position ensures that the buttons at the top
				# of the form are in the same order as those at
				# the bottom.

				self.contents.insert (button_counter, btn)
				self.contents.append (btn)

				# note that we have one more button in the
				# row of buttons at the top (and bottom) of
				# the form.  Remember, this is used so that we
				# know where to insert the next button at the
				# top of the form.

				button_counter = button_counter + 1

		# add a reset button if necessary (to top & bottom of form)

		if self.reset:
			# add the button (btn) to the top and bottom of the
			# form.  Inserting at the button_counter position
			# ensures that the buttons at the top of the form are
			# in the same order as those at the bottom.

			self.contents.insert (button_counter, self.reset)
			self.contents.append (self.reset)

			# note that we have one more button in the row of
			# buttons at the top (and bottom) of the form. 
			# Remember, this is used so that we know where to
			# insert the next button at the top of the form.

			button_counter = button_counter + 1

		# note that we wanted our buttons centered

		# place centering tags at the beginning of the contents and
		# after the final button at the top

		self.contents.insert (0, '<CENTER>')
		self.contents.insert (button_counter + 1, '</CENTER>')

		# place centering tags before the first button at the bottom of
		# the form, and then at the end (after the last button on the
		# bottom of the form)

		self.contents.insert (len (self.contents) - button_counter, \
			'<CENTER>')
		self.contents.append ('</CENTER>')

		# now produce the output string by handling each standard
		# keyword (to build the form definition) and then appending
		# all the contents (which also include the buttons).

		s = ['\n<FORM METHOD="%s"' % self.method]
		if self.cgi:
			s.append (' ACTION="%s"' % self.cgi)
		if self.enctype:
			s.append (' ENCTYPE="%s"' % self.enctype)
		if self.target:
			s.append (' TARGET="%s"' % self.target)
		if self.name:
			s.append (' NAME="%s"' % self.name)
		if self.onSubmit:
			s.append (' onSubmit="%s"' % self.onSubmit)
		s.append ('>\n')

		for item in self.contents:		# add the string rep of
			s.append (str (item))		# each item in contents.

		s.append ('\n</FORM>\n')		# end the form
		return string.join (s, '')		# convert to a string

### End of Class: WTS_Form ###


class WTS_Document (HTMLgen.SeriesDocument):
	# Concept:
	#	IS: A WTS_Document is a single WTS web page.  It derives from
	#		HTMLgen.SeriesDocument and overrides the __init__
	#		method to provide a few WTS-specific features:
	#			* each document is created as a CGI response,
	#			  rather than as a static web page
	#			* a default title is specified
	#			* there is no onLoad event handler
	#			* allowing zero or more Meta tags
	#	HAS: A WTS_Document has the attributes (instance variables) of
	#		the HTMLgen.SeriesDocument class.  No new attributes
	#		have been added; this class only defines a few of the
	#		defaults differently, like the page title, whether it
	#		is produced as a CGI response, and what resource file
	#		to use.  See HTMLgen's documentation for more explicit
	#		description of the fields.
	#	DOES: A WTS_Document can have HTMLgen-compatible objects added
	#		(appended) to it and it can be written either to a file
	#		or to stdout (as a CGI response).
	# Implementation:
	#	This class shares its implementation details with
	#	HTMLgen.SeriesDocument.  Please see that class for attributes
	#	(instance variables) and the like.  This class only overrides
	#	the __init__ method to allow a few WTS-specific defaults.

	def __init__ (self,
		**kw		# optional set of keyword parameters (names
				# corresponding to the object's attributes) to
				# alter the defaults for values in self.
		):
		# Purpose: initialize the object with some WTS-specific default
		#	values (as mentioned in the class comments)
		# Returns: nothing
		# Assumes: values specified by keyword parameters are the
		#	appropriate type for that attribute (instance variable)
		# Effects: initializes this object as an HTMLgen.SeriesDocument
		#	with some WTS-specific default parameters (as described
		#	in the class comments above).  Then, process any
		#	keyword parameters to override the defaults as needed.
		# Throws: KeyError if one of the keywords specified as a
		#	parameter does not correspond to an object attribute.

		global RESOURCE_FILE	# needed by HTMLgen to identify
					# formatting styles.

		# do a basic init for an HTMLgen SeriesDocument, but with some
		# WTS-specific keyword parameters.  The defaults identify:
		# that we will create each document as a CGI response (rather
		# than as a static web page); a default title which may be
		# overridden; and no onLoad handler.

		# note that subclasses of WTS_Document may set their own
		# appropriate titles (for the HTML document produced, which
		# goes in the browser title bar and at the top of the document)
		# in their __init__ methods by setting self.title after calling
		# this __init__ function.

		HTMLgen.SeriesDocument.__init__ (self, RESOURCE_FILE,
			cgi = 1,
			title = 'WTS : Work Tracking System',
			onLoad = None)

		# set up the list for Meta tags

		self.meta = MetaList ()

		# process the keywords that came into this method.  Note that
		# self.__dict__ is a dictionary with keys being the names of
		# the object's attributes (instance variables).  This code is
		# taken from the __init__ method of HTMLgen.SeriesDocument.

		for item in kw.keys():
			if self.__dict__.has_key(item):
		 		self.__dict__[item] = kw[item]
			else:
				# using the standard exception KeyError to
				# denote a bad keyword parameter is the
				# mechanism used by HTMLgen.  Let's use it
				# here, too, to be consistent.

				raise KeyError, `item` + \
					' not a valid parameter of the ' + \
					'WTS_Document class.'
		return

### End of Class: WTS_Document ###


class Error_Screen (WTS_Document):
	# Concept:
	#	IS: An Error_Screen is an HTML page which presents the user
	#		with a bulleted list of errors and gives him/her the
	#		choice of correcting them or aborting the current
	#		operation.
	#	HAS: Two buttons: Fix (which goes back to the previous screen
	#		so that the user can make changes) and Abort (which
	#		aborts the current operation).  Has a list of errors
	#		which we present to the user in a bulleted list.  Has
	#		three other (optional) parameters which specify how to
	#		handle an abort operation, including:  which cgi script
	#		to call, which tracking record number to unlock, and
	#		how many screens to go back.
	#	DOES: extends WTS_Document by providing a setup method which
	#		creates the error notification screen.  Commonly one
	#		would create an Error_Screen object, invoke setup, and
	#		the invoke its write method to send it out to the user.
	# Implementation:
	#	No new fields are added; the internal representation is the
	#	same as that for WTS_Document.  We only add a new setup method
	#	which produces an error notification screen in that document.

	def setup (self,
		errors,			# list of strings describing errors
					# which were found / encountered.
		abort_cgi = None,	# optional string specifying the name
					# of the CGI script to call if the
					# Abort button is clicked.
		back_count = 1,		# optional number of screens to go back
					# if the Abort button is clicked.
		tr_num = None		# optional number of the tracking
					# record to unlock if the Abort button
					# is clicked.
		):
		# Purpose: produce an error notification screen in self, given
		#	the input parameters
		# Returns: nothing
		# Assumes: nothing
		# Effects: see Purpose.  Once setup has completed, this screen
		#	may be written out using the write method.
		# Throws: nothing
		# Notes: The Buttons added to this document (Fix and Abort) use
		#	Javascript to instruct the user's browser to go back in
		#	its history list.  The Fix button has Javascript to go
		#	back to the previous screen, thus allowing the user to
		#	make changes in the data he/she entered.  If no value
		#	is specified for abort_cgi, the Abort button has 
		#	Javascript ot go back two screens, presumably going to
		#	the one before the editing process began.  If an
		#	abort_cgi was defined, then the Abort button uses
		#	Javascript to call specified CGI script and specify the
		#	tr_num and back_count in a GET-style submission.


		# add the initial explanatory message

		self.append (HTMLgen.Text ('The following errors were ' + \
			'encountered.  Please click Fix to go back and fix ' + \
			'them, or Abort to just abort the entire operation.'))

		# append the list of errors in a bulleted format

		self.append (HTMLgen.BulletList (errors))

		# create a new form object

		frm = WTS_Form (abort_cgi, name = 'AbortForm')

		# define the Fix button here (with Javascript to go back one
		# screen when clicked)

		frm.append (Button ('Fix', 'window.history.go(-1)'))

		# if the caller specified an abort_cgi, then we need to make
		# a button with Javascript to load that CGI and include the
		# necessary fields in a GET-style submission.

		if (abort_cgi <> None):

			# the basic Javascript command specifies the CGI to
			# call and the number of screens to go back 

			href = 'window.location.href="' + abort_cgi + \
				'?BackCount=' + str (back_count)

			# if a tracking record to unlock was specified, then
			# we also need to include that

			if tr_num:
				href = href + '&TR_Nr=' + str (tr_num)

			# finally, terminate the double-quote in href, build it
			# into a Button labeled Abort, and add that button to
			# the form

			frm.append (Button ('Abort', href + '"') )

		# if the caller did not specify an abort_cgi, then the Abort
		# button and the Fix button can both just be Back buttons

		else:
			# define the Abort button to use Javascript to go back
			# two screens

			frm.append (Button ('Abort', 'window.history.go(-2)'))

		# and, append the finished form to the document

		self.append (frm)
		return

### End of Class: Error_Screen ###


class Exception_Screen (WTS_Document):
	''' provides a method for producing an exception-notification screen.
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self, exc_type, exc_value, trace):
		'''
		#
		# Requires:	exc_type - string giving type of exception
		#		exc_value - string giving value of exception
		#		trace - a list of tuples with the exception
		#			traceback information
		#		
		# Effects:	generates screen-specific info for an exception
		#		screen and puts it in self
		# Modifies:	self
		'''
		# add the initial explanatory message

		self.append (HTMLgen.Text ('An exception occured and ' + \
			'was caught by the file indicated above.  Please ' + \
			'contact the programmer listed in the footer and ' + \
			'give him/her the following information:'))

		# append the list of errors in a bulleted format

		self.append (HTMLgen.BulletList ([ 'Type: ' + exc_type, \
			'Value: ' + exc_value, 'Traceback:' ]))

		# process the traceback information to generate a nice table

		tbl = HTMLgen.TableLite (cellpadding = 5, border = 1, \
			align = 'center')
		tbl.append (HTMLgen.TR (HTMLgen.TH ('File'), \
			HTMLgen.TH ('Line'), HTMLgen.TH ('Function'), \
			HTMLgen.TH ('Text')))

		for item in trace:
			fn = item [0][ string.rfind (item [0], '/') + 1: ]
			tbl.append (HTMLgen.TR (HTMLgen.TD (fn), \
				HTMLgen.TD (str (item[1])), 
				HTMLgen.TD (str (item[2])),
				HTMLgen.TD (str (item[3])) ))

		# and, append the traceback table

		self.append (tbl)

### End of Class: Exception_Screen ###


class GoTo_Screen (WTS_Document):
	# Concept:
	#	IS: a screen which simply replaces itself immediately with
	#		another specified one
	#	HAS: the URL to the screen we want to load
	#	DOES: a GoTo_Screen should be initialized, setup, and then
	#		written out to the user's browser.
	# Implementation:
	#	We use Javascript to handle loading the new screen.
	# Notes:
	#	When we instantiate this class, we should specify that
	#	onLoad = "go_to()".  For example:
	#		screen = GoTo_Screen (onLoad = 'go_to ()')

	def setup (self,
		url	# URL to which we should go
		):
		# Purpose: set up this screen to go to the given "url"
		# Returns: None
		# Assumes: nothing
		# Effects: see Purpose
		# Throws: nothing

		# append the JavaScript code to the document

		self.append (HTMLgen.Script (code = '''
			function go_to () {
				window.location.replace ("%s");
				}
			window.onload = go_to();''' % url))

		return

### End of Class: GoTo_Screen ###


class Message_Screen (WTS_Document):
	''' provides a method for producing a screen which only gives a message
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self, message = '', back_count = 1, load_tr = None):
		'''
		#
		# Requires:	message - string containing the message,
		#		back_count - integer number of screens for the
		#			ok button to go back.
		#		load_tr - integer TR number to load, if we
		#			don't want to go back
		# Effects:	generates screen-specific info for a simple
		#		message-notification screen and puts it in self
		# Modifies:	self
		'''
		# if the user gave us a negative back count, then just make
		# it positive

		if back_count < 0:
			back_count = -back_count

		# add the initial explanatory message

		self.append (HTMLgen.Text (message))

		# append the JavaScript code (to go back) to the document

		go_back = '''function go_back () {
			window.history.go (-%s);
			}''' % back_count

		if load_tr != None:
			go_back = '''function go_back() {
				window.location.replace("tr.detail.cgi?TR_NR=%s");
				}''' % load_tr

		self.append (HTMLgen.Script (code = go_back))

		# we need to add an Ok button which references the above
		# JavaScript.  To be displayed, this button must appear on
		# a form.

		frm = WTS_Form (name = 'BackForm')

		# define the the button on the form, and add the form to self

		frm.append (Button ('Ok', 'go_back ()'))

		self.append (frm)

class Unlock_Screen (WTS_Document):
	''' provides a method for producing a screen which gives a message 
	# about unlocking a locked TR.
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self, tr_nr = '', back_count = 1, exc_value = ''):
		'''
		#
		# Requires:	message - string containing the message,
		#		back_count - integer number of screens for the
		#			ok button to go back.
		# Effects:	generates screen-specific info for a simple
		#		message-notification screen and puts it in self
		# Modifies:	self
		'''
		# if the user gave us a negative back count, then just make
		# it positive

		if back_count < 0:
			back_count = -back_count

		message = '''The tracking record (TR #%d) is being edited and
                        was %s.  Please press Back to go back to the Detail
			screen.
                        Or if have communicated with the other user and
                        learned that he/she is no longer editing the TR, you
                        may unlock it by clicking the Unlock button.''' % (
				tr_nr, exc_value)

		# add the initial explanatory message

		self.append (HTMLgen.Text (message))

		# append the JavaScript code (to go back) to the document

		self.append (HTMLgen.Script (code = \
			'function go_back () { window.history.go (-' + \
			str (back_count) + ') }'))

		self.append (HTMLgen.Script (code = \
			'''function unlock() {
				window.location.replace(
					"tr.edit.cgi?TrackRec=%s&unlock=1");
			}''' % tr_nr))

		# we need to add an Ok button which references the above
		# JavaScript.  To be displayed, this button must appear on
		# a form.

		frm = WTS_Form (name = 'BackForm')

		# define the the button on the form, and add the form to self

		frm.append (Button ('Back', 'go_back ()'))
		frm.append (Button ('Unlock', 'unlock()'))

		self.append (frm)

### End of Class: Message_Screen ###


class TrackRec_ShortForm_Screen (WTS_Document):
	''' provides a method for producing a screen to allow entry of a new
	#	tracking record using the Short Form
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self,
		tr		# a new TrackRec object
		):
		'''
		#
		# Requires:	nothing
		# Effects:	generates screen-specific info to allow the
		#		entry of a new tracking record and puts it in
		#		self
		# Modifies:	self
		'''
		global WTS_HOME_PAGE
		self.title = PREFIX + ': New Tracking Record - Short Form'

		# get formatting info for the tracking record (as a list of
		# HTMLgen objects)

		obj_list = tr.html_New_ShortForm ()

		# insert Javascript code to facilitate watching for double-clix

		self.script = [
			HTMLgen.Script (src = "Notes.js"),
			HTMLgen.Script (src = "wts.js"),
			]

		# create the form for the entry screen

		frm = WTS_Form ('tr.new.save.cgi', \
			name = 'EntryForm', \
			submit = HTMLgen.Input (type = 'submit', value = 'Save',
				name = 'Save'), \
			reset = HTMLgen.Input (type = 'reset'), \
			buttons = [ Button ('Cancel', 'window.history.go (-1)'),
				Button (PREFIX + ' Home',
				'window.location.href = "%s"' % WTS_HOME_PAGE)],
			onSubmit = "return enoughTimeElapsed()")

		# add the TrackRec info to the form, then the form to the doc

		for obj in obj_list:
			frm.append (obj)
		self.append (frm)

### End of Class: TrackRec_ShortForm_Screen ###


class Password_Screen (WTS_Document):
	# Concept:
	#	IS:	a screen with two text-entry field which the user may
	#		use to change his/her WTS password
	#	HAS:	see IS
	#	DOES:	collects two copies of the new password to be set, and
	#		passes them on to "../cgi/change.password.cgi"
	# Implementation:
	#	derives from WTS_Document, and uses a setup() method to create
	#	the screen itself

	def setup (self,
		username	# string; name of the current user
		):
		# Purpose: create the password screen
		# Returns: nothing
		# Assumes: nothing
		# Effects: sets up self
		# Throws: nothing
		# Notes: The "username" is included in bold and italics on the
		#	screen to remind the user whose password is being
		#	changed.

		global WTS_HOME_PAGE

		self.title = "Change WTS Password for %s" % username

		# create the data entry form

		frm = WTS_Form ('change.password.cgi',
			name = 'PasswordForm',
			enctype = 'multipart/form-data',
			submit = HTMLgen.Input (type = 'submit',
				value = 'Change',
				name = 'Change'),
			reset = HTMLgen.Input (type = 'reset'),
			buttons = Button (PREFIX + ' Home',
				'window.location.href = "%s"' % WTS_HOME_PAGE))

		frm.append (HTMLgen.P (),
			HTMLgen.Text ('Enter the new password twice for '),
			HTMLgen.Strong (HTMLgen.Emphasis (username)),
			HTMLgen.Text (', then click the "Change" button.'),
			HTMLgen.P ())

		frm.append (HTMLgen.Input (type = 'password',
				name = 'password1',
				size = 15,
				maxlength = 15,
				llabel = 'Enter New Password: '),
			HTMLgen.P())

		frm.append (HTMLgen.Input (type = 'password',
				name = 'password2',
				size = 15,
				maxlength = 15,
				llabel = 'Re-Enter New Password: '),
			HTMLgen.P())

		self.append (frm)
		return


### End of Class: Password_Screen ###


class New_TrackRec_Screen (WTS_Document):
	''' provides a method for producing a screen to allow the entry of a
	#	new tracking record
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self, tr):
		'''
		#
		# Requires:	tr - tracking record to use in setting up this
		#			screen.  (Use the values in tr as the
		#			defaults for each field on the form.)
		# Effects:	generates screen-specific info to allow the
		#		entry of a new tracking record and puts it
		#		in self.  Note that we now add a "Cancel" button
		# Modifies:	self
		'''
		global WTS_HOME_PAGE
		self.title = PREFIX + ': New Tracking Record Screen'

		# prepare the list of extra buttons (the home page and the
		# cancel button)

		buttonList = [ Button ('Cancel', 'window.history.go (-1)'), 
				Button (PREFIX + ' Home',
				'window.location.href = "%s"' % WTS_HOME_PAGE) ]

		# insert Javascript code to facilitate watching for double-clix

		self.script = [
			HTMLgen.Script (src = "Notes.js"),
			HTMLgen.Script (src = "wts.js"),
			]

		frm = WTS_Form ('tr.new.save.cgi', name = 'TrEntryForm',
			submit = HTMLgen.Input (type = 'submit',
				value = 'Save',
				name = 'Save'),
			reset = HTMLgen.Input (type = 'reset'),
			buttons = buttonList,
			onSubmit = "return enoughTimeElapsed()")

		# add the tracking record info to the form (as a list of
		# HTMLgen objects)

		obj_list = tr.html_Edit_LongForm ()
		for obj in obj_list:
			frm.append (obj)
		self.append (frm)	# add the form to the document

### End of Class: New_TrackRec_Screen ###


class TR_Notification_Screen (WTS_Document):
	''' provides a method for producing a screen which notifies the user
	#	of the creation of a new tracking record, and which gives
	#	him/her the option of creating another one or returning to
	#	the WTS home page.
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self, tr_num, msg = ""):
		'''
		#
		# Requires:	tr_num - integer key of the tracking record
		#			which was created
		#		msg - string; the message which was sent to the
		#			routing group (if any)
		# Effects:	generates screen-specific info to notify the
		#		user of the creation of a new tracking 
		#		record and puts it in self
		# Modifies:	self
		'''
		global WTS_HOME_PAGE

		self.title = PREFIX + \
			': Tracking Record Number Notification Screen'

		# now, add the necessary message

		self.append (HTMLgen.Text ('Your tracking record was ' + \
			'saved and was assigned the number ') )

		self.append (HTMLgen.Href ('tr.detail.cgi?TR_Nr=' + \
			str (tr_num), 'TR ' + str (tr_num)))

		self.append (HTMLgen.P ())

		if len (msg) > 0:
			self.append ("Routing Response:")
			self.append (HTMLgen.PRE (msg))
			self.append (HTMLgen.P ())

		# append the buttons (must be on a form)

		frm = WTS_Form ()
		frm.append (Button (PREFIX + ' Home', \
			'window.location.href="%s"' % WTS_HOME_PAGE))
		frm.append (Button ('Create Another New TR (Long Form)', \
			'window.location.href="tr.new.cgi"'))
		frm.append (Button ('Create Another New TR (Short Form)', \
			'window.location.href="tr.new.sf.cgi"'))
		self.append (frm)

### End of Class: TR_Notification_Screen ###


class TrackRec_Detail_Screen (WTS_Document):
	# Concept:
	#	IS: an HTMl page which displays the entire contents of one
	#		tracking record (singly or as part of a series of
	#		tracking records).
	#	HAS: a list of HTMLgen objects which represent the page to be
	#		written out
	#	DOES: provides two primary methods - setup() and write()
	# Implementation:
	#	derives from WTS_Document and contains a WTS_Form

	def setup (self,
		tr_numbers,		# string; contains a comma-separated
					# series of tracking record keys yet to
					# be displayed
		previous_tr_screen = 0,	# boolean; 1 if there is a previous
					# tracking record display screen, 0 if
					# there is not.  (This tells us whether
					# to display a Previous button or not)
		expanded = 0		# boolean; if non-zero, then we should
					# display an expanded TR detail page
					# (with enhanced dependency info)
		):
		# Purpose: set up this TrackRec_Detail_Screen to contain the
		#	details of the first tracking record in tr_numbers
		# Returns: nothing
		# Assumes: nothing
		# Effects: Retrieves (using the TrackRec module) the HTMLgen
		#	objects which represent the first tracking record
		#	specified in tr_numbers.  Builds these into the detail
		#	display page which is stored in this object.
		# Throws: progagates - 1. ValueError if the specified tracking
		#	record cannot be found in the database.
		#	2. wtslib.sqlError if we have problems in querying the
		#	database.

		global WTS_HOME_PAGE
		self.title = PREFIX + ': Tracking Record Detail Screen'

		# take the first number from tr_numbers for display

		temp_tr_numbers = string.split ( \
			string.translate (tr_numbers, \
			string.maketrans ('',''), 'TR '), ',')
		tr_num = string.atoi (temp_tr_numbers [0])

		# rebuild tr_numbers without the deleted characters ('TR ')

		tr_numbers = string.join (temp_tr_numbers, ',')

		# now, remove it from the list of those yet to display,
		# and convert the list back into a comma-separated string

		del temp_tr_numbers [0]

		# also remove any TR 0, which is used as a flag on the
		# query results screen.

		if '0' in temp_tr_numbers:
			temp_tr_numbers.remove ('0')

		if len (temp_tr_numbers) > 0:
			temp_tr_numbers = wtslib.list_To_String ( \
				temp_tr_numbers, ',')
		else:
			temp_tr_numbers = None

		# get HTMLgen objects for the specified tracking record, with
		# the method determined by whether we wanted an "expanded"
		# display or not

		tr = TrackRec.TrackRec (tr_num)	# loads specified track rec
		if not expanded:
			obj_list = tr.html_Display ()
		else:
			obj_list = tr.html_Display (1)

		del tr				# delete the track rec

		# get a list of the buttons to put on the form...  first the
		# Previous button, if we had a previous detail screen

		if previous_tr_screen <> 0:
			button_list = [ Button ('Previous', \
				'window.history.go (-1)')]
		else:
			button_list = []

		# then the Edit button...

		button_list.append (Button ('Edit',
			'if (enoughTimeElapsed()) ' + \
			'window.location.href="' + \
			'tr.edit.cgi?TrackRec=' + str (tr_num) + '"'))

		# then an Expand or Contract button as needed...
		#	basic_url is the url for a contracted display

		basic_url = 'tr.detail.cgi?TR_Nr=%s&Prev_TR_Screen=%s' % \
			(tr_numbers, previous_tr_screen)

		if expanded:
			button_list.append (Button ('Contract',
				'window.location.replace ("%s")' % basic_url))
		else:
			button_list.append (Button ('Expand',
				'window.location.replace ("%s&Expanded=1")' % \
				basic_url))

		# now, if there are more TR listed, we need a Next button...

		if temp_tr_numbers:
			submit_button = HTMLgen.Input (type = 'submit', name = \
				'Next', value = 'Next')
		else:
			submit_button = None

		# finally, the WTS Home button...

		button_list.append (Button (PREFIX + ' Home', \
			'window.location.href="' + WTS_HOME_PAGE + '"'))

		# insert Javascript code to facilitate watching for double-clix

		self.script = [
			HTMLgen.Script (src = "Notes.js"),
			HTMLgen.Script (src = "wts.js"),
			]

		# create the form for the tracking record

		frm = WTS_Form ('tr.detail.cgi',
			method = 'GET',
			name = 'TrDetailForm',
			submit = submit_button,
			buttons = button_list)

		# leading space before the table
	
		frm.append (HTMLgen.BR ())

		# add the tracking record info

		for obj in obj_list:			# visible info
			frm.append (obj)

		# trailing space after the form
	
		frm.append (HTMLgen.BR ())

		# hidden fields identifying the list of tracking records yet
		# to be displayed, and the state of whether there was a
		# previous tracking record display screen.

		if temp_tr_numbers:
			frm.append (HTMLgen.Input (type = 'hidden', \
				name = 'TR_Nr', value = temp_tr_numbers) )
		frm.append (HTMLgen.Input (type = 'hidden', value = 1, \
			name = 'Prev_TR_Screen') )

		# add some Meta tags (to force a reload after Editing)

		self.meta.append (HTMLgen.Meta (equiv="pragma",
			content="no-cache"))
		self.meta.append (HTMLgen.Meta (equiv="Expires",
			content="Tue, 26-Oct-1965 12:00:00"))
		self.meta.append (HTMLgen.Meta (equiv="Expires", content="NOW"))
		self.meta.append (HTMLgen.Meta (equiv="last modified",
			content="NOW"))

		# add the current date & time, centered above the table

		self.append (HTMLgen.Center (HTMLgen.Small ('Displayed: %s' % \
			wtslib.current_Time ())), HTMLgen.P () )

		# now, add the form to the document in self

		self.append (frm)

### End of Class: TrackRec_Detail_Screen ###


class TrackRec_Edit_Screen (WTS_Document):
	''' provides a method for producing a screen to edit a given tracking
	#	record
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self, tr):
		'''
		#
		# Requires:	tr - the TrackRec object we'd like to edit
		# Effects:	generates screen-specific info to allow the
		#		editing of an existing tracking record and puts
		#		it in self
		# Modifies:	self
		'''
		self.title = PREFIX + ': Tracking Record Edit Screen'

		# insert Javascript code to facilitate watching for double-clix

		self.script = [
			HTMLgen.Script (src = "Notes.js"),
			HTMLgen.Script (src = "wts.js"),
			]

		# get HTMLgen objects for the specified tracking record (as a
		# list of HTMLgen objects)

		obj_list = tr.html_Edit_LongForm ()

		# create the form for the tracking record

		frm = WTS_Form ('tr.edit.save.cgi', name = 'TrDetailForm', \
			submit = HTMLgen.Input (type = 'submit', name = \
				'Save', value = 'Save'), \
			reset = HTMLgen.Input (type = 'reset', name = \
				'ResetTr', value = 'Reset'),
			buttons = [ Button ('Cancel', \
				'window.location.href="tr.bailout.cgi?' \
				+ 'BackCount=2&TR_Nr=' + str (tr.num()) + \
				'"'), \
				Button (PREFIX + ' Home', \
					'window.location.href="' + \
				WTS_HOME_PAGE + '"') ],
			onSubmit = "return enoughTimeElapsed()"
			)

		# leading space before the table
	
		frm.append (HTMLgen.BR ())

		# add the tracking record info

		for obj in obj_list:			# visible info
			frm.append (obj)

		# trailing space after the form
	
		frm.append (HTMLgen.BR ())

		# now, add the form to the document in self

		self.append (frm)

### End of Class: TrackRec_Edit_Screen ###


class Query_Result_Screen (WTS_Document):
	''' provides a method for producing a screen which displays a grid
	#	of query results
	#
	# Requires:	inherits from WTS_Document
	# Effects:	see above
	# Modifies:	self
	'''
	def setup (self, clean_results, hidden_fields, status_date = None):
		'''
		#
		# Requires:	clean_results - a list of dictionaries, each of
		#			which contains the full information to
		#			display (in a row) for one tracking
		#			record.  Each dictionary should have
		#			the same keys (fieldnames).
		#		hidden_fields - a dictionary of information
		#			which should be included as hidden
		#			fields on the form.  These could be used
		#			to carry over information about how to
		#			sort the query results, and which
		#			tracking records to display.
		# Effects:	builds and runs the queries for the given
		#		clean_dict.  Then uses the results to generate
		#		screen-specific info to present the tracking
		#		record query result screen.
		# Modifies:	self
		'''
		self.title = PREFIX + ': Tracking Record Query Results Screen'

		obj_list = TrackRec.build_Query_Table (clean_results)

		# create the form for buttons and table.

		frm = WTS_Form ('tr.detail.cgi', name = 'QryResForm', \
			method = 'GET',
			submit = [ \
				HTMLgen.Input (type = 'submit', name = \
					'Detail', value = 'Detail'),
				HTMLgen.Input (type = 'submit', name = \
					'ReDisplay', value = 'ReDisplay', \
					onClick = \
					"document.QryResForm.action='" + \
					"tr.query.results.cgi'"),
				HTMLgen.Input (type = 'submit', name = \
					'As Text', value = 'As Text', \
					onClick = \
					"document.QryResForm.action='" + \
					"tr.query.results.cgi'") ],
			reset = HTMLgen.Input (type = 'reset', name = \
				'Reset', value = 'Reset'),
			buttons = [ Button (PREFIX + ' Home',
					'window.location.href="' + \
					WTS_HOME_PAGE + '"'),
				    Button ('Click All',
			'''for (var i = 0; i < QryResForm.TR_Nr.length; i++) {
				QryResForm.TR_Nr [i].checked =
					!QryResForm.TR_Nr [i].checked; }''') ] )

		# leading space, then count of the records

		frm.append (HTMLgen.BR ())
		recCount = len (clean_results)
		if recCount == 0:
			recCountMsg = "no records returned"
		elif recCount == 1:
			recCountMsg = "1 record returned"
		else:
			recCountMsg = "%d records returned" % recCount
		frm.append (HTMLgen.Center (recCountMsg))

		# leading space, then message about Status Date, if non-None

		if status_date is not None:
			frm.append (HTMLgen.BR(),
				HTMLgen.Center ("shows last Status set " + \
					"in the range %s" % status_date))

		# leading space before the table
	
		frm.append (HTMLgen.BR ())

		# now add the objects for the table

		for item in obj_list:
			frm.append (item)

		# trailing space after the table
	
		frm.append (HTMLgen.BR ())

		# add the necessary hidden fields to the form:  (These will
		# be used if we do a Re-Display, to remember the desired
		# fields to show and the selected sorting information.)

		for field in hidden_fields.keys ():
			frm.append (HTMLgen.Input (type = 'hidden', \
				name = wtslib.underscored (field), \
				value = hidden_fields [field]) )

		# add a hidden field with TR_Nr = 0, so that if the user checks
		# no boxes before doing a redisplay, he/she won't get back all
		# tracking records.

		frm.append (HTMLgen.Input (type = 'hidden', name = 'TR_Nr',
			value = '0'))

		# add the current date & time, centered above the table

		self.append (HTMLgen.Center (HTMLgen.Small ('Displayed: %s' % \
			wtslib.current_Time ())), HTMLgen.P () )

		# now, add the form to the document in self

		self.append (frm)

### End of Class: Query_Result_Screen ###


class Status_Grid_Screen (WTS_Document):
	# Concept:
	#	IS: an HTML-formatted page which shows a grid of Status by
	#		Area or Type
	#	HAS: standard attributes inherited from WTS_Document
	#	DOES: sends the page (self) to stdout

	def setup (self,
		row_type,	# string; specified analysis by "Area" or "Type"
		date_range,	# string; range of dates examined
		tbl		# HTMLgen object representing the table of
				# results
		):
		# Purpose: set up the innards of this page
		# Returns: nothing
		# Assumes: nothing
		# Effects: adds to self -- only run this once!
		# Throws: nothing

		self.title = PREFIX + ': Status by %s Grid' % row_type

		btns = []
		btns.append (Button (PREFIX + ' Home', \
			'window.history.go (-2)'))
		if row_type == 'Area':
			other_type = 'Type'
		else:
			other_type = 'Area'
		btns.append (Button ('Show as Grid by %s' % other_type,
			'window.location.href="tr.status.grid.cgi?' + \
			'DateRange=%s&RowType=%s"' % (date_range, other_type)))

		frm = WTS_Form (buttons = btns)
		frm.append (HTMLgen.Center ('Date Range: %s' % \
			date_range, HTMLgen.P()))
		frm.append (tbl)
		frm.append (HTMLgen.P ())
		self.append (frm)
		return

### End of Class: Status_Grid_Screen ###

class Help_Screen (WTS_Document):
	# Concept:
	#	IS: an HTML-formatted page which shows a page of help
	#	HAS: standard attributes inherited from WTS_Document
	#	DOES: sends the page (self) to stdout

	def setup (self,
		fieldname,	# name of the field for which to display help
		description,	# explanation of the field
		toQuery,	# how to query the field
		cvName		# name of the associated CV, if any
		):
		# Purpose: set up the innards of this page
		# Returns: nothing
		# Assumes: nothing
		# Effects: adds to self -- only run this once!
		# Throws: nothing

		self.title = PREFIX + ': Help -- %s' % fieldname
		terms = [
			('Description', description + str(HTMLgen.P())),
			('To Query', toQuery + str(HTMLgen.P())),
			]
		if cvName:
			terms.append ( ('Controlled Vocabulary',
				Controlled_Vocab.getCVtables (cvName)) )
		self.append (HTMLgen.DefinitionList (terms))
		return

#--MODULE FUNCTIONS-------------------------------------------

def gen_Exception_Screen (filename):
	''' outputs an HTML screen which informs the user that an exception
	#	occurred, identifies the file that caught it, gives a list of
	#	error messages, and asks him/her to contact the programmer. 
	#	Serves to encapsulate the class Exception_Screen since it is
	#	used to often.
	#
	# Requires:	filename - string name of the file reporting the
	#		exception.
	# Effects:	see above
	# Modifies:	no side effects
	'''

	# retrieve the exception information from sys and traceback

	type = str (sys.exc_type)
	value = str (sys.exc_value)
	trace = traceback.extract_tb (sys.exc_traceback)

	doc = Exception_Screen (title = PREFIX + \
		': Exception Caught by ' + filename)
	doc.setup (type, value, trace)

	# send the document to stdout, and delete it

	doc.write ()
	del doc


def gen_GoTo_Screen (url):
	doc = GoTo_Screen()
	doc.setup(url)
	doc.write()
	del doc

def gen_Message_Screen (page_title, message, back_count = 1, load_tr = None):
	''' outputs an HTML screen which presents the given title and message,
	#	along with an Ok button which goes back the specified number
	#	of screens.  (serves as a wrapper for the Message_Screen class
	#	which could be used frequently)
	#
	# Requires:	page_title - string; title of the page
	#		message - string; message to be displayed
	#		back_count - optional integer specifying the number
	#			of screens to go back in the history list.
	#			The default is: 1
	# Effects:	generates an HTML document with the given title, and
	#		which presents the given message.  An Ok button goes
	#		back in the history list the specified number of times.
	#		Sends this document to stdout (in a CGI response format)
	# Modifies:	no side effects
	'''
	doc = Message_Screen (title = page_title)
	doc.setup (message, back_count, load_tr)

	# now send the page to stdout and delete it

	doc.write ()
	del doc

def gen_Unlock_Screen (page_title, tr_nr, exc_value, back_count = 1):
	doc = Unlock_Screen (title = page_title)
	doc.setup (tr_nr, back_count, exc_value)

	doc.write()
	del doc
