from socket import *
import regex
import string

error = 'PopMail.error'
CRLF = '\r\n'


# We need 15 extra bytes to download each email, plus 1 for each digit in the
# total number of bytes.  IE if the size of the message was 1304, we would 
# need to download 15+4 extra bytes.  Set to 30 because if we need more than 
# 15 decimal places, we don't want the message.
EXTRA_BYTES = 30

# The maximum amount of bytes to download by default
DEFAULT_MSG_SIZE = 1024

# Purpose: retrieve and delete messages from a mail server
# Returns: a list of strings, each containing one message (including 
# 	headers), that were on the server.
# Assumes: the server/port combo is a valid pop3 mailserver 
# Effects: Connects to the specifed mailserver, sends the username and 
# 	password, IN PLAIN TEXT and logs in.  Once logged in, it checks for 
# 	messages, downloads any that are found, and deletes them before 
#	logging out.
# Throws: PopMail.error if the username/password combo is invalid or the
# 	mailbox is locked.
# Notes: ALL MESSAGES ARE DELETED FROM THE SERVER ONCE DOWNLOADED
def getPOPMail(
	User,
	Pass,
	Host,
	Port = None
	):
	
	err = regex.compile('^-ERR')
	
	host = Host
	#if no port is specified, lookup the standard port of a pop3 server.
	if Port == None or Port == '' :
		port = getservbyname('pop3','tcp')
	else : port = Port

	#connect to the server and download it's greeting.
	s = socket(AF_INET,SOCK_STREAM)
	s.connect(host,port)
	resp = s.recv(DEFAULT_MSG_SIZE)

	#login
	s.send('USER ' + User + CRLF)
	resp = s.recv(DEFAULT_MSG_SIZE)
	if err.match(resp) != -1 :
		raise error , 'The username is not vaild on ' + HOST_NAME	
	
	s.send('PASS ' + Pass + CRLF)
	resp = s.recv(DEFAULT_MSG_SIZE)
	if err.match(resp)  != -1 :
		raise error , 'The username/password is invalid or the '\
			      'mailbox is in use.'
	
	#Get the number of messages we have
	s.send('STAT' + CRLF)
	resp = s.recv(DEFAULT_MSG_SIZE)
	r = regex.compile('\+OK \([^ ]+\) \(.*\)')
	rc = r.search(resp)
	
	#if there is some sort of problem with the regex, we have no messages.
	if rc != -1 :
		msgs = string.atoi(r.group(1))
		size = string.atoi(r.group(2))
	else :
		msgs = 0
		size = 0
		
	newMail = []
	
	#Get each message size from the server
	for i in range(1, msgs+1) :
		s.send('LIST ' + str(i) + CRLF)
		msgInfo = s.recv(DEFAULT_MSG_SIZE)
		#and as long as the message number is valid
		
		if err.match(msgInfo) == -1 :
			rc = r.search(msgInfo)
			#deterime how many bytes to download
			if rc != -1 :
				size = string.atoi(r.group(2)) + EXTRA_BYTES
			else :
				size = 0
			#pull the entire message off the server
			s.send('RETR ' + str(i) + CRLF)
			newMsg = s.recv(size)
			while regex.search('\r\n\.\r\n$',newMsg) < 0  :
				newMsg = newMsg + s.recv(size)
			#add it to our list
			newMail.append(newMsg)
			#and delete it from the server
			s.send('DELE ' + str(i) + CRLF)
			s.recv(DEFAULT_MSG_SIZE)
	#logoff from the server
	s.send('QUIT' + CRLF)
	s.close()
	return newMail