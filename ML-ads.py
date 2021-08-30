#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# MLADS.PY
#
# This script downloads the calendar of Mittag-Leffler and
# outputs speakers, titles and abstracts as a text file.
#
# Usage
#
# python MLads.py --start 20100301 --stop 20100308 --output message.txt
#
# The above run will download all items in the calendar from 20100301
# (March 1, 2010) to 20100308 (March 8, 2010), output the generated
# text file in message.txt.
#
# Compatibility
#
# Compatible with both Python 2 and Python 3
#
# Requires modules bs4 (BeautifulSoup4) and lxml which are installed as follows:
# python -m pip install bs4
# python -m pip install lxml

try:
    import htmlentitydefs # Python 2
except ImportError:
    import html.entities # Python 3

try:
    from urllib2 import urlopen # Python 2
except ImportError:
    from urllib.request import urlopen # Python 3

import urllib.parse

import datetime, copy, codecs, optparse, os, re, sys
strptime = datetime.datetime.strptime
from bs4 import BeautifulSoup, BeautifulStoneSoup
import lxml

############################################################################
# spanToDate
############################################################################

def spanToDate( span_el ):
    created = span_el['content']
    timestring = span_el.string or ""
    timestring = timestring.strip()

    m = re.match(r"^\s*([a-zA-Z]+ \d+)\s*([0-9:]+)\s*-\s*([0-9:]+)\s*$", timestring)
    if m: # August 31 15:00 - 16:00
        date = strptime(m.group(1),'%B %d').date()
#       date = parse(date).date()
        startTime = m.group(2)
        endTime = m.group(3)
    else:
      m = re.match(r"^\s*(\d+ [a-zA-Z]+)\s*([0-9:]+)\s*-\s*([0-9:]+)\s*$", timestring)
      if m: # 31 August 15:00 - 16:00
          date = strptime(m.group(1),'%d %B').date()
#         date = parse(date).date()
          startTime = m.group(2)
          endTime = m.group(3)
      else:
          print( "%s: error: Incorrect date/time format (%s)" % \
              (os.path.basename(sys.argv[0]), timestring) )
          sys.exit()

    created = datetime.datetime.fromisoformat(created).date()

    # Date is missing year, use created year
    date = date.replace(year=created.year)

    if date < created:
        print( "Warning: date (%s) is earlier than created (%s)." % (date, created) )
    return (date,startTime,endTime)


############################################################################
# fetchSeminars
############################################################################

def fetchSeminars(url):
    print( "Fetching seminars" )

    seminars = []

    page = urlopen(url)
    info = page.info()
    content = BeautifulSoup(page,features="lxml")

    for seminar_el in content.findAll('div', {'class':'view-mode-seminar_list'}):
        seminar = {}
        date_el = seminar_el.find('div', {'class':'date'}).find('span')
        (seminar['date'],seminar['startTime'],seminar['endTime']) = spanToDate( date_el )
        title_el = seminar_el.find('h4', {'class':'node-title'})
        seminar['title'] = (title_el.find('a').string or "").strip()
        speaker_el = seminar_el.find('h5')
        seminar['speaker'] = (speaker_el.string or "").strip()
        semurl_el = seminar_el.find('div', {'class':'read-more'})
        semurl = semurl_el.find('a')['href'] or ""

        try:
            seminar['speaker'] = BeautifulStoneSoup(seminar['speaker'], convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]
            seminar['title'] = BeautifulStoneSoup(seminar['title'], convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]
        except:
            pass

        if seminar['date'] >= options.start and seminar['date'] <= options.stop:
 #      print( "* %s (%s-%s), %s: %s" % (date,startTime,endTime,speaker,title) )
            seminars.append( fetchSeminar( urllib.parse.urljoin(url,semurl),seminar) )
        else:
            print( "Skipping seminar on %s", seminar['date'] )
    return seminars

############################################################################
# fetchSeminar
############################################################################

def fetchSeminar( url, check ):
    seminar = {}

    print( "Fetching: %s (%s-%s), %s: %s" % (check['date'], check['startTime'], check['endTime'], check['speaker'], check['title']) )

    page = urlopen(url)
    info = page.info()
    content = BeautifulSoup(page,features="lxml")
    mainContent = content.find('div', {'id':'main-content'})
    title_el = mainContent.find('h1',{'class':'node-title'})
    seminar['title'] = (title_el.string or "").strip()

    headers = mainContent.findAll('h4')
    if len(headers) != 3:
        raise Exception( "Wrong number of headers: %d (should be 3)" % (len(headers),) )
    # headers[0] is program name, ignore.
    (seminar['date'],seminar['startTime'],seminar['endTime']) = spanToDate( headers[1].find('span') )
    seminar['speaker'] = (headers[2].string or "").strip()

    abstract_el = mainContent.find('div', {'class':'description-text'})
    seminar['abstract'] = '\n'.join( [t.string.strip() for t in abstract_el.find_all(text=True)] )

    # Check seminar with check
    for key in check:
        if seminar[key] != check[key]:
            raise Exception( "Key %s does not match" % (key,) )

    if seminar['date'] != check['date']:
        raise Exception( "Date does not match (%s vs %s)" % (date.isoformat(),checkDate.isoformat()) )
    if seminar['startTime'] != check['startTime'] or seminar['endTime'] != check['endTime']:
        raise Exception( "Time does not match (%s-%s vs %s-%s)" % (startTime,endTime,checkStartTime,checkEndTime) )
    if seminar['speaker'] != check['speaker']:
        raise Exception( "Speaker does not match (%s vs %s)" % (speaker,checkSpeaker) )
    if seminar['title'] != check['title']:
        raise Exception( "Title does not match (%s vs %s)" % (title,checkTitle) )
    return seminar


############################################################################
#  MAIN
############################################################################



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
                  help="name of destination file of abstracts", metavar="FILE")

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

if errs != "":
    print( "%s" % (errs,) )
    parser.print_help()
    sys.exit()

if options.start > options.stop:
    print( "%s: error: Start date must be before stop date" % \
          (os.path.basename(sys.argv[0])) )
    sys.exit()


# OPEN OUTPUT FILE

if options.output:
    try:
        output = codecs.open(options.output, mode='w', encoding='utf-8')
    except:
        print( "%s: error: Unable to open file %s for writing" % \
            (os.path.basename(sys.argv[0]), options.output) )
        sys.exit()


# DOWNLOAD ALL SEMINARS BETWEEN START AND STOP DATES
#
# This information is stored in the data structure
#
# seminars = [seminar1, seminar2, ...]
#
# where
#
# seminar = [date, starttime, stoptime, speaker, title, calender_url]

re_no = re.compile(u'No calendar events were found')

url = "http://mittag-leffler.se/research-programs/current-program/seminars"
seminars = fetchSeminars(url)

# OUTPUT SEMINARS
if options.output:
    for seminar in seminars:
        output.write( "TITLE: %s: %s\n" % (seminar['speaker'],seminar['title']) )
        output.write( "START: %s %s\n" % (seminar['date'].isoformat(),seminar['startTime']) )
        output.write( "STOP: %s %s\n" % (seminar['date'].isoformat(),seminar['endTime'] ) )
        output.write( "SPEAKER: %s\n" % (seminar['speaker'],) )
        output.write( "ABSTRACT: %s\n" % (seminar['abstract'],) )
        output.write( "\n\n" )
    output.close()
