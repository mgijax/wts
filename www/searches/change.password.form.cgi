#!/usr/local/bin/python

# display a form which allows the user to change his/her WTS password

import os
import sys
import Configuration
import screenlib

try:
	page = screenlib.Password_Screen ()	# create the new, blank screen
	page.setup (os.environ ['REMOTE_USER'])	# set it up with the user's name
	page.write ()				# write it out to the user
except:
	gen_Exception_Screen ('change.password.form.cgi')
