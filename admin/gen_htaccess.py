#!./python

# Name: gen.htaccess
# Purpose: generate www/.htaccess file during the installation of WTS
# Note: run ONLY from the admin directory
	  
import sys
if '.' not in sys.path:	 
	sys.path.insert(0,'.')
import os
import Configuration

data_path = Configuration.config['DATADIR']
htuser_path = os.path.join(data_path,'htaccess/wts.user')
htgroup_path = os.path.join(data_path,'htaccess/wts.group')

s = ''
s = s + 'AuthUserFile ' + htuser_path + '\n'
s = s + 'AuthGroupFile ' + htgroup_path + '\n'
s = s + 'AuthName WTS \n'
s = s + 'AuthType Basic \n\n'

s = s + '<Limit GET POST PUT> \n' + 'require group mgi \n' + '</Limit>\n'

htaccess_path = '../www/.htaccess'

fp = open(htaccess_path,'w')
fp.write(s)
fp.close()

