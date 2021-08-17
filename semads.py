#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime, copy, codecs, optparse, os, re, sys, htmlentitydefs, urllib2
strptime = datetime.datetime.strptime
from BeautifulSoup import BeautifulSoup
from BeautifulSoup import BeautifulStoneSoup


# SEMADS.PY
#
# This script downloads the calender of the smc and
# formats the information as a text file.
#
# Usage
#
# python semads.py --start 20100301 --stop 20100308 --output message.txt
#
# The above run will download all items in the calendar from 20100301
# (March 1, 2010) to 20100308 (March 8, 2010), output the generated
# text file in message.txt.


# READ COMMAND-LINE OPTIONS

def check_date(option, opt, val):
    try:
        return strptime(val,'%Y%m%d').date()
    except ValueError:
        raise optparse.OptionValueError(
            "option %s: invalid date value: %r" % (opt, val))

class ExtOption (optparse.Option):
    TYPES = optparse.Option.TYPES + ("date",)
    TYPE_CHECKER = copy.copy(optparse.Option.TYPE_CHECKER)
    TYPE_CHECKER["date"] = check_date

parser = optparse.OptionParser(option_class=ExtOption)
parser.add_option("--start", action="store", type="date",
                  help="start date", metavar="YYYYMMDD", dest="start")
parser.add_option("--stop", action="store", type="date",
                  help="stop date", metavar="YYYYMMDD", dest="stop")
parser.add_option("--output", action="store", type="string",
                  help="name of destination file of email message", metavar="FILE")

(options, args) = parser.parse_args()


# CHECK OPTIONS

errs = ""
if not options.output:
    errs += "%s: error: No output file specified\n" % \
            (os.path.basename(sys.argv[0]),)
if not options.start:
    errs += "%s: error: No start date specified\n" % \
            (os.path.basename(sys.argv[0]),)
if not options.stop:
    errs += "%s: error: No stop date specified\n" % \
            (os.path.basename(sys.argv[0]),)

if errs<>"":
    print "%s" % (errs,)
    parser.print_help()
    sys.exit()

if options.start > options.stop:
    print "%s: error: Start date must be before stop date" % \
          (os.path.basename(sys.argv[0]))
    sys.exit()


# OPEN OUTPUT FILE

if options.output:
    try:
        output = codecs.open(options.output, mode='w', encoding='utf-8')
    except:
        print "%s: error: Unable to open file %s for writing" % \
            (os.path.basename(sys.argv[0]), options.output)
        sys.exit()


# FIND ALL DAYS TO DOWNLOAD

download_days = [options.start]
oneday = datetime.timedelta(days=1)
while download_days[-1] < options.stop:
    nextday = download_days[-1] + oneday
    download_days.append(nextday)


# DOWNLOAD ALL SEMINARS BETWEEN START AND STOP DATES
#
# This information is stored in the data structure
#
# seminars = [[<date object>, [seminar, ...]], ...]
#
# where
#
# seminar = [starttime, stoptime, seminar_serie, speaker, title, calender_url]

seminars = []
for day in download_days:

    seminars.append([day, []])

    url = "http://www.math-stockholm.se/kalender"
    url += "?date=" + day.isoformat()
    url += "&length=1"
    #url += "&l=en_UK"

    page = urllib2.urlopen(url)
    info = page.info()  
    content = BeautifulSoup(page)

    seminar_list = []

    if content.find('h2',text=re.compile(u'Kalenderhändelser saknas')):
        continue

    for seminar_el in content.findAll('li', {'class':'calendar__event'}):

        starttime = ""
        stoptime = ""
        seminarserie = ""
        speaker = ""
        title = ""
        location = ""
        calendar_url = ""

        # Seminar serie
        seminarserie = seminar_el.find('div', {'class': 'calendar__eventinfo--bold'})
        seminarserie = seminarserie.string or ""
        seminarserie = seminarserie.strip()


        # Speaker and title
        try:
            speaker, title = seminar_el.find('div').find('a')['title'].split(":",1)
        except ValueError:
            speaker = ""
            title = seminar_el.find('div').find('a')['title']

        speaker = speaker.strip()
        title = title.strip()

        try:
            speaker = BeautifulStoneSoup(speaker, convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]
            title = BeautifulStoneSoup(title, convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]
        except:
            pass

        # Start and stop time
        starttime = seminar_el.find('span', {'class': 'startTime'})
        starttime = starttime.string or ""
        starttime = starttime.strip()

        stoptime = seminar_el.find('span', {'class': 'endTime'})
        try:
            stoptime = stoptime.string or ""
        except:
            stoptime = ""
        #stoptime = stoptime.strip()
        if len(stoptime) < 6:
            stoptime = " - "+ stoptime
            
        # Calendar url
        calendar_url = seminar_el.find('div').find('a')['href']
        calendar_url = calendar_url.split("?")[0]
        calendar_url = "http://www.math-stockholm.se" + calendar_url

        # Location
        for el in seminar_el.findAll('div'):
            bel = el.find('span', {'class': 'calendar__eventinfo--bold',})
            if bel and bel.contents[0] == 'Plats: ':
                location = bel.findNext('a').contents[0].strip()
                location = BeautifulStoneSoup(location, convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]
                break

        # Collect info
        seminar = [starttime, stoptime, seminarserie, speaker, title, location,
                   calendar_url,]

        seminar_list.append(seminar)

    seminars[-1][1] = seminar_list


# PRINT THE SEMINARS

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday")
MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

day = options.start
startdate = "%s %d, %4d," % (MONTHS[day.month-1], day.day, day.year)
day = options.stop
stopdate = "%s %d, %4d" % (MONTHS[day.month-1], day.day, day.year)

body = ""
body += "SEMINARS\n"
body += "========\n"
body += "\n"
body += "This is an automatically generated summary of the Stockholm Mathematics Center\n"
body += "web calender for seminars from %s to %s.\n\n" % (startdate, stopdate)

body += "Send subscription requests to kalendarium@math-stockholm.se.\n\n"

for daysem in seminars:
    day = daysem[0]
    seminar_list = daysem[1]

    if not seminar_list:
        continue

    headline = "%s, %s %d, %s" % (WEEKDAYS[day.weekday()].upper(), 
                                 MONTHS[day.month-1],
                                 day.day,
                                 day.year)

    body += "\n%s\n\n" % (headline,)

    for seminar in seminar_list:
        if seminar[0] or seminar[1]:
            body += "%5s%5s\n" % (seminar[0], seminar[1],)
        if seminar[3]:
            body += "       %s\n" % (seminar[3],)
        if seminar[4]:
            body += "       %s\n" % (seminar[4],)
        if seminar[5]:
            body += "       %s\n" % (seminar[5],)
        if seminar[2]:
            body += "       %s\n" % (seminar[2],)
        if seminar[6]:
            body += "       %s\n" % (seminar[6],)
        body += "\n"


# OUTPUT SEMINARS

if options.output:
    for line in body:
        output.write(line)
    output.close()
