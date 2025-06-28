#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
# line "Seminars" to the recipients listed in the file emails.txt
# logging in as boij to smtp.kth.se

import argparse
import getpass
import re
import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate
from datetime import date

# reasonable emails should have an @, at least one . afterwards, and no whitespace.
# the list is curated by hand anyway so should not be a problem
EMAIL_REGEX = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

SEND_AS = "kalendarium@math-stockholm.se"
# SEND_AS = "kalendarium@math.kth.se"


def parse_emails(file):
    with open(file) as file:
        ret = []
        for line in file:
            line = line.strip()
            if line.startswith("#"):
                continue
            email_address, *expiry_date = line.split()
            if len(expiry_date) > 1:
                print("Too many entries in one line: {line}")
                continue
            if len(expiry_date) == 1:
                expiry_date = expiry_date[0]
                try:
                    expiry_date = date.fromisoformat(expiry_date)
                except ValueError as e:
                    raise ValueError(
                        f"second entry in {line} should be a date (YYYYMMDD)"
                    ) from e
                if expiry_date < date.today():
                    print(f"Remove: {email_address}, past expiry date {expiry_date}")
            elif re.fullmatch(EMAIL_REGEX, email_address) is None:
                print(f"Invalid email: {email_address}")
            else:
                ret.append(email_address)
        return ret


def read_file(file):
    with open(file) as file:
        return file.read()


# READ COMMAND-LINE OPTIONS
parser = argparse.ArgumentParser()

parser.add_argument(
    "--sendlist",
    type=parse_emails,
    help="file with list of email addresses",
    metavar="EMAILS_FILE",
    required=True,
)
parser.add_argument(
    "--message",
    type=read_file,
    help="file with message body",
    metavar="MESSAGE_FILE",
    required=True,
)
parser.add_argument("--subject", type=str, help="subject line", default="Seminars")
parser.add_argument(
    "--username", type=str, help="KTH username of sender", required=True
)

# parser.add_option("--ssl", action="store_true", dest="ssl",
#                  help="connect via SSL")
# parser.add_option("--socks", action="store_true", dest="socks",
#                  help="Use SOCKS proxy")
# parser.set_defaults(ssl=False)

args = parser.parse_args()


# SETUP PROXY IF REQUESTED
# if options.socks:
#     import socks
#     socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, 'localhost', 1492)
#     socks.wrapmodule(smtplib)
#
# # There seems to be IPv6-problems wrapping socks around smtplib in this way.
# # Perhaps need to explicitly connect using socket.connect((host,port))


# SEND EMAILS

with smtplib.SMTP("smtp.kth.se", 587) as server:
    server.starttls()
    password_prompt = f"{args.username}@kth.se's password:"
    while True:
        try:
            password = getpass.getpass(password_prompt)
            server.login(args.username, password)
            break
        except smtplib.SMTPAuthenticationError:
            password_prompt = (
                f"Login unsuccessful, reenter {args.username}@kth.se's password:"
            )
        except smtplib.SMTPException as e:
            print("Unable to login to smtp.kth.se")
            raise e

    for index, receiver in enumerate(args.sendlist, start=1):
        # m = Message()
        m = MIMEText(args.message, _charset="utf-8")
        m["To"] = receiver
        m["From"] = SEND_AS
        m["Subject"] = Header(args.subject, charset="utf-8")
        m["Date"] = formatdate(localtime=True)

        # m.set_payload(body)
        # m.set_charset('utf-8')

        try:
            server.sendmail(SEND_AS, [receiver], m.as_string())
            print(f"Sent to {receiver} ({index}/{len(args.sendlist)})")
        except Exception as e:
            print(f"Error sending to {receiver}")
            print(e)
        time.sleep(0.3)
