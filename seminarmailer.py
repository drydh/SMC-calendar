#!/usr/bin/python
# -*- coding: utf-8 -*-

from email.Message import Message
from email.Header import Header
#from email.mime.text import MIMEText
from email.MIMEText import MIMEText

import codecs, email, smtplib, getpass, optparse, os, sys, time


# SEMINARMAILER.PY
#
# This script sends an email message
#
# Usage
#
# python seminarmailer.py --message input.txt --subject "Seminars" \
#   --sendlist emails.txt --username boij
#
# The above run will send the message in the file input.txt with subject
# line "Seminars" to the recipients listed in the file emails.txt.


# READ COMMAND-LINE OPTIONS

parser = optparse.OptionParser()
parser.add_option("--sendlist", action="store", type="string",
                  help="file with list of email addresses", metavar="FILE",
                  dest="sendlist_file")
parser.add_option("--message", action="store", type="string",
                  help="name of source file of email message", metavar="FILE")
parser.add_option("--subject", action="store", type="string",
                  help="subject line of email message", metavar="FILE")
parser.add_option("--username", action="store", type="string",
                  help="KTH username of user", metavar="FILE")

(options, args) = parser.parse_args()


# CHECK OPTIONS

errs = ""
if not options.sendlist_file:
    errs += "%s: error: No sendlist specified\n" % \
            (os.path.basename(sys.argv[0]),)
if not options.message:
    errs += "%s: error: No message file specified\n" % \
            (os.path.basename(sys.argv[0]),)
if not options.subject:
    errs += "%s: error: No subject specified\n" % \
            (os.path.basename(sys.argv[0]),)
if not options.username:
    errs += "%s: error: No username specified\n" % \
            (os.path.basename(sys.argv[0]),)

if errs<>"":
    print "%s" % (errs,)
    parser.print_help()
    sys.exit()


# OPEN MESSAGE FILE

if options.message:
    try:
        input = codecs.open(options.message, mode='r', encoding='utf-8')
        #input = codecs.open(options.message, mode='r')
    except:
        print "%s: error: Unable to open file %s for reading" % \
            (os.path.basename(sys.argv[0]), options.message)
        sys.exit()


# OPEN EMAIL ADDRESS FILE

sendlist_file = False
if options.sendlist_file:
    try:
        sendlist_file = open(options.sendlist_file, "r")
    except:
        print "%s: error: Unable to open file %s for reading" % \
            (os.path.basename(sys.argv[0]), options.sendlist_file)
        sys.exit()

GENERIC_DOMAINS = "aero", "asia", "biz", "cat", "com", "coop", \
    "edu", "gov", "info", "int", "jobs", "mil", "mobi", "museum", \
    "name", "net", "org", "pro", "tel", "travel"

def valid_email(emailaddress, domains = GENERIC_DOMAINS):
    """Checks for a syntactically invalid email address."""
    
    # Email address must be 7 characters in total.
    if len(emailaddress) < 7:
        return False # Address too short.
    
    # Split up email address into parts.
    try:
        localpart, domainname = emailaddress.rsplit('@', 1)
        host, toplevel = domainname.rsplit('.', 1)
    except ValueError:
        return False # Address does not have enough parts.

    # Check for Country code or Generic Domain.
    if len(toplevel) != 2 and toplevel not in domains:
        return False # Not a domain name.

    for i in '-_.%+.':
        localpart = localpart.replace(i, "")
    for i in '-_.':
        host = host.replace(i, "")

    if localpart.isalnum() and host.isalnum():
        return True # Email address is fine.
    else:
        return False # Email address has funny characters.

sendlist = []
if sendlist_file:
    for line in sendlist_file.readlines():
        email = line.strip()
        if valid_email(email):
            sendlist.append(email)


# READ INPUT FILE

body = u""
for line in input.readlines():
    body += line

body = body.encode('utf-8')


# SEND EMAILS

sender = "kalendarium@math-stockholm.se"
#sender = "kalendarium@math.kth.se"
receiver = ""
subject = options.subject or "Seminars"

server = smtplib.SMTP('smtp.kth.se',587)
server.starttls()
psswd = getpass.getpass(options.username + "@kth.se's password:")
try:
    server.login(options.username, psswd)
except:
    print "Unable to login to smtp.kth.se"
    sys.exit()

for addr in sendlist:

    receiver = addr
    
    #m = Message()
    m = MIMEText(body, _charset='utf-8')
    m['To'] = receiver
    m['From'] = sender
    m['Subject'] = Header(subject, 'utf-8')
    #m.set_payload(body)
    #m.set_charset('utf-8')
    
    server.sendmail(sender, [receiver], m.as_string())

    print "Skickat till %s" % (receiver,)

    time.sleep(2)

server.close()

