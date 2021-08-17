Needs Python 2 or Python 3 installed with bs4 (BeautifulSoup) and lxml.

Usage: 
1. Make sure calendar, semads.py and seminarmailer.py are in the same directory.
2. Update "user" in "calendar" file to reflect your KTH username.
3. Update "python" in "calendar" file if necessary.
4. Make sure that the calendar file is executable (e.g. use chmod).
5. Run ./calendar from the directory containing the files. 
6. The script will create the week's email and display it in the nano editor. 
7. Check the email and press ctrl+o to save any changes.
8. When the email has been checked press ctrl+x.
9. Press y to send the email or ctrl+c to exit. 
10. When promted, type in your KTH password to send the email. 

Notes:
- You can run these files from any computer. 
- If you are running these files from your own computer there is an option to
  use a socks proxy for the mailer. 
