#!/usr/local/bin/python
import Configuration
from wtslib import send_Mail
from TrackRec import TrackRec
from popmail import *
import sys
import regex
import time

# various error types
error = 'PopMail.error'
error_subj = error +'InvalidSubj'

# used for error emails sent to users
maint = 'Josh Winslow'
maintAddr = 'jw@informatics.jax.org'

# Purpose: Extract the sending userid, TR number, and body of the message
#	from an eMail message.
# Returns: a tuple containing a userID, a trNumber, and the body of the 
#	message, all as strings
# Assumes: The eMail message passed in is formatted to RFC 822 and that there
#	is a blank line after the last header, before the body.  Also, the
#	"Subject:" line must only consist of TR <TR NUMBER>.  EX:
#	Subject: TR 1241
#	will return 1241 as the trNumber
# Effects: Finds the username from the "From:" line, the TR from the 
#	"Subject:" line and takes the remainder of the email after the 
#	headers, not including a signature, as the body.
# Throws: PopMail.errorInvalidSubj if the "Subject:" line is not formatted 
#	properly.
#	  PopMail.error if it cannot deterime who sent the message.
# Notes: Any text after a --\r\n will be deleted from the body.  It is 
#	assumed that this text is part of a signature.
def parseMailMessage(
	eMail
	):

	#Search the from line for the userid
	#this assumes that all eMail will come from internal addresses
	uidRegEx = regex.compile('From: .*<\([^@]+\)@')
	rc = uidRegEx.search(eMail)
	if rc == -1 :
		# if the eMail doesn't have a valid return address
		# its probably spam, in which case, error out
		raise error , 'Invalid "From:" line.'
	else :
		userID = uidRegEx.group(1)
	
	#Search the subject line for TR a number, then a newline
	sbjRegEx = regex.compile('Subject: .*[Tt][Rr] \([0-9]+[\r\n]+\)')
	rc = sbjRegEx.search(eMail)
	if rc == -1 :
		#If we don't find it, raise an exception
		raise error_subj , 'Message from user, ' + userID + \
			', did not contain a valid subject.\r\n' 
	else :
		trNum = string.atoi(sbjRegEx.group(1))
	
	# Regular Expressions to help find the begining and end of the body.
	bodyStartRegEx = regex.compile('\r\n\r\n')
	sigStartRegEx = regex.compile('[^-]--\r\n')
	bodyEndRegEx = regex.compile('\r\n.\r\n')
	
	#The 4 extra character eliminate the required CRLFs from the begining
	#of the body.
	start = bodyStartRegEx.search(eMail) + 4
	end = sigStartRegEx.search(eMail,start)
	#if there is no sig included in this email
	if end == -1 :
	#find the end of the text
		end = bodyEndRegEx.search(eMail,start)
	body = eMail[start:end]
	return (userID, trNum, body)

def sendErrorMsg(errorText) :

	r = regex.compile(', \(.*\),')
	r.search(errorText)
	uid = r.group(1)
	error_subj_msg = 'In a recent email you sent to ' +\
			 user + ', the system detected the '\
			 'following error:\r\n\r\n'\
			 + sys.exc_value + '\r\n'\
			 'Your message was not added to the '\
			 'progress notes.  Please resend your'\
			 ' message.\r\n\r\n'\
			 'The correct format for the subject '\
			 'line is:\r\n'\
			 'Subject: TR VALID_TR_NUMBER\r\n'\
			 'I.E. Subject: TR 1001\r\n\r\n'\
			 'If you need assistance with this '\
			 'feature, please contact ' + maint +\
			 ' at ' + maintAddr + '.'
	send_Mail(user,
		  uid,
		  'Problem with your recent email',
		  error_subj_msg) 
	return

# if executed from command line we want to run our WTS specific code to
# extract the TR number and body and update the progress notes of that 
# tr to reflect the email.
if __name__ == '__main__':

	#masst and wts will have different accounts, so we need to specify
	#which one we want to run in the configuration files.
	config = Configuration.Configuration()
	user = config['USERNAME']
	pwd  = config['PASSWORD']
	host = config['HOST_NAME']
	#download the mail
	mail = getPOPMail(user, pwd,host,None)
	#for all the messages
	for i in mail :
		try :
			#See if we can parse it
			sender,trNum,text = parseMailMessage(i)
			
			#if we can, load up the tr so we can edit it
			try :
				tr = TrackRec(trNum)
			except :
				raise error_subj , 'In message sent by user, '+\
					sender + ', the TR number was invalid'\
					'.\r\n'
			try :
				tr.lock()
			except:
				raise error , 'In message sent by user, '+\
					sender + ', the TR was locked.\r\n'
			
			#get the existing notes
			notes = tr.getAttribute('Progress Notes')
			string.strip(notes)
			
			#determine if there are no notes yet
			r = regex.compile('^<[Pp][Rr][Ee]>[ \r\n\t]*None'\
					  '[ \r\n\t]*</[Pp][Rr][Ee]>$')
			rc = r.search(notes)
			
			#if so, wipe the none field out
			if rc != -1 :
				notes =''
				
			#get the date and time
			timestamp = time.asctime(time.localtime(time.time()))
			#create our new note
			newNote = '<LI><B> ' + timestamp + ' ' + sender +\
			' </B><BR>' + text + '<P>'
			#append it to the existing notes
			notes = notes + newNote
			#and save it
			tr.setAttribute('Progress Notes',notes)
			tr.save()
			tr.unlock()
		#If we can't determine which TR the email was about, send an 
		#automatic reply to the user to let them know what went 
		# wrong.
		except error_subj  :
			sendErrorMsg(sys.exc_value)			
		#If we can't determine the user that sent the email, just 
		#skip to the next one.
		except error :
			sendErrorMsg(sys.exc_value)

		#if there are any other errors
		except :
			#print the error to the console and update the maintainer
			print sys.exc_value
			send_Mail(user,maintAddr,"WTS error",sys.exc_value)
