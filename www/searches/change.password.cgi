#!/usr/local/bin/python

# cgi for the "Change WTS Password" form
# accepts two fields: password1 and password2

import os
import sys
import cgi
import string
import Configuration
import wtslib
import screenlib
import HTPassword

# main program

try:
	dict = wtslib.FieldStorage_to_Dict (cgi.FieldStorage ())

	if not (dict.has_key ('password1') and dict.has_key ('password2')):
		screenlib.gen_Message_Screen ('Missing Data',
			'Your new password must be entered in both fields')

	elif (dict ['password1'] != dict ['password2']):
		screenlib.gen_Message_Screen ('Password Discrepancy',
			'''The values of the two fields do not match.  Please
			re-enter your new password in each.''')

	elif len (string.strip (dict ['password1'])) == 0:
		screenlib.gen_Message_Screen ('Password Must Not Be Empty',
			'''Your password must be non-empty.  Please choose a
			different one.''')

	else:
		# open the password file, set the new password for the current
		# user, and close the file.  Let any exceptions be caught by
		# the outer "try..except"

		dir = '%s/htaccess' % Configuration.config['DATADIR']
		pwd_file = HTPassword.HTPassword ('%s/wts.user' % dir)
		pwd_file.setPassword (os.environ ['REMOTE_USER'], 
			dict ['password1'])
		pwd_file.close ()

		screenlib.gen_Message_Screen ('Password Changed',
			'Your password was changed.', 2)
except:
    screenlib.gen_Exception_Screen ('change.password.cgi')
