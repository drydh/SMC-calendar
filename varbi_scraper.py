#!/usr/bin/env python3

#import contextlib
import datetime
import re
import csv

import requests
from bs4 import BeautifulSoup # >= 4.4.0.

import sys

title_strong_keywords = ["mathematics", "matematik",
                  "mathematical", "matematisk",
                  "numerical analysis", "numerisk analays",
                  "\blogic", "\blogik"]

title_weak_keywords = ["mathematic", # s, al
                       "matemati", # k, sk
                       "analys", # is
                       "algebra",
                       "number theory", "talteori",
                       "topolog", # y, i
                       "geometr", # y, i, ical
                       "\blogi", # c, k (and don't match geological etc)
                       "numerical", "numerisk", # (analys)
                       "optimization", "optimering",
                       "computational", "beräkning",
                       "statisti", # cs, cal, k, sk
                       "probability", "sannolikhet",
                       "complex",
                       "modeling", "modelling",
                       "\bdata\b"]

ad_strong_keywords = ["department of mathematics", "institutionen för matematik", "KTH mathematics", "computational mathematics", "applied mathematics"]
ad_weak_keywords = ["mathematics", "matematik"] # Don't want "mathematical"
anti_keywords = ["School of Electrical Engineering", "Skolan för elektroteknik", "EECS",
                 "Chemistry, Biotechnology and Health", "kemi, bioteknologi och hälsa", "CBH",
                 "Architecture and Built Environment", "Skolan för arkitektur och samhällsbyggnad", "ABE",
                 "School of Industrial Engineering and Management", "Skolan för industriell teknik och management", "ITM", "Department of Physics"]

# PhD subjects
subjects = ["Mathematics","Applied and computational mathematics"]
anti_subjects = ["Computer Science","Solid Mechanics"]

# re.escape(k) for k in keywords
title_strong_pattern = re.compile(r"|".join(title_strong_keywords), re.IGNORECASE)
title_weak_pattern = re.compile(r"|".join(title_weak_keywords), re.IGNORECASE)
ad_strong_pattern = re.compile(r"|".join(ad_strong_keywords), re.IGNORECASE)
ad_weak_pattern = re.compile(r"|".join(ad_weak_keywords), re.IGNORECASE)
anti_pattern = re.compile(r"|".join(anti_keywords), re.IGNORECASE)

subj_pattern = re.compile(r"Third-cycle subject:\s*(.*)")
subjects_pattern = re.compile(r"|".join(subjects), re.IGNORECASE)
anti_subjects_pattern = re.compile(r"|".join(anti_subjects), re.IGNORECASE)

organizations = {
    177: { "name": "KTH",
           "categories": { 1445: 'Assistant professor',
                           1446: 'Associate professor',
                           1447: 'Full professor',
                           1448: 'Lecturer (adjunkt)',
                           1449: 'PhD student', # doktorand
                           1450: 'Research engineer',
                           1451: 'Researcher / postdoc',
#                           1452: 'Undergraduate assistant',
#                           1453: 'Administrative / assistant', # Technical, administrative and service personnel
                          } },
    1218: { "name": "SU",
            "categories": { 1659: 'Assistant professor',
                            1658: 'Associate professor', # / Senior lecturer / Universitetslektor
                            1657: 'Full professor',
                            1656: 'Researcher',
                            1655: 'Postdoc',
                            1654: 'PhD student', # doktorand
                            # 1653: 'Research assistant / Forskningsassistent / forskningssekreterare / antagningshandläggare / ... '
                           }
           }
}

try:
    import requests_cache
    session = requests_cache.CachedSession(cache_name='varbi_cache', backend='sqlite',
                                           expire_after=60*30) # Expire after 30 minutes
    print(f"Using cache ({session.cache.db_path}).", file=sys.stderr)
    def is_cached(response):
        return response.from_cache
    def get_url( url, **kw ):
        response = session.get( url, **kw )
        if( response.status_code == 429 ):
            raise TooManyRequests(response)
        print(" [CACHED] " if is_cached(response) else "", end="", file=sys.stderr)
        return response
except ImportError:
    session = requests.Session()
    def is_cached(response):
        return False
    def get_url( url, **kw ):
        return session.get( url, **kw )

class TooManyRequests(Exception):
    """Too many requests"""
    def __init__(self, response):
        super().__init__(f'Too many requests. Retry after: {response.headers["Retry-After"] if "Retry-After" in response.headers else "(unknown)"} s')


######################################################################
# Fetch JSON from Varbi
######################################################################

def find_varbi_jobs():
    math_jobs = []

    for entry in fetch_all_jobs():
        math = False
        not_math = False
#        print( entry["department"] )
        if title_weak_pattern.search(entry["title"]) and not anti_pattern.search(entry["department"] or ""):
            # Potential math job
            print(f"- Job ID {entry['id']}: ",end="", file=sys.stderr)
            if title_strong_pattern.search(entry["title"]):
                # Math job (due to title)
                print(f"MATHEMATICS (title)", file=sys.stderr)
                math = True
            else:
                # Fetch html ad and investigate.
                print(f"fetching... ", end="", file=sys.stderr)
                response = get_url( entry["ad_url"] )
                soup = BeautifulSoup(response.text, features='lxml')

                # Look for PhD subjects
                subjects = soup.find_all(string=subj_pattern)
                if len(subjects) == 1:
                    print(f"PhD subject: ", end="", file=sys.stderr)
                elif len(subjects) > 1:
                    print(f"MULTIPLE PhD subjects: ", end="", file=sys.stderr)
                for result in subjects:
                    m = subj_pattern.match(result)
                    if m:
                        subj = m[1]
                        if( len(subj) == 0 ):
                            subj = result.next_element
                        print(subj, end="", file=sys.stderr)
                        if( subjects_pattern.match(subj) ):
                            print(" (MATHEMATICS).", file=sys.stderr)
                            math = True
                        elif( anti_subjects_pattern.match(subj) ):
                            print(" (definitely not mathematics).", file=sys.stderr)
                            not_math = True
                        else:
                            print(" (probably not mathematics).", file=sys.stderr)
                    else:
                        print("ERROR", end="", file=sys.stderr)
                if not math and not not_math:
                    if soup.find(string=ad_strong_pattern):
                        # Math job (mentions Department of Mathematics)
                        print(f"MATHEMATICS (department).", file=sys.stderr)
                        math = True
                    elif soup.find(string=ad_weak_pattern) and not soup.find(string=anti_pattern):
                        # Perhaps math job (mentions Mathematics)
                        print(f"perhaps MATHEMATICS?", file=sys.stderr)
                        math = True
                    else:
                        print("not mathematics.", file=sys.stderr)
                        not_math = True
        if math:
            math_jobs.append( entry )

    return math_jobs

def fetch_all_jobs():
    print("Fetching all VARBI jobs:", file=sys.stderr)
    return [ trim_job_entry(entry)
             for (org_id,org) in organizations.items()
             for (cat_id,cat) in org["categories"].items()
             for entry in fetch_all_pages( api_jobs_url(org_id, cat_id),
                                           {'Accept-Language': 'en,sv'}, # prefer english
#                                           {},
                            f'{org["name"]}, {cat}' )
            ]

def api_jobs_url(org,cat):
    return f"https://api.varbi.com/v1/jobs?filter[organization]={org}&filter[category]={cat}" # &include=categories,organization,taxonomy,employment_type


# Fetch all pages using limit / offset

def fetch_all_pages(url, headers, info_str):
    print(f"  Fetching {info_str}.", end="", file=sys.stderr)
    
    limit = 100
    offset = 0
    while True:
       response = get_url( url+f"&limit={limit}&offset={offset}", headers=headers )
       json = response.json()
       yield from json["data"]
       if offset+limit >= json["meta"]["total"]:
           break
       offset += limit
    print("", file=sys.stderr)

def trim_job_entry(entry):
    attrs = entry["attributes"]
    links = entry["links"]
    rels = entry["relationships"]
#    print( attrs["translations"], file=sys.stderr)
#    if( len( attrs["translations"]["languages"]["available"] ) < 2 ):
#        print( attrs["translations"], file=sys.stderr )
    
    return {
        "id": entry["id"],
        "ref": attrs["reference"],
        "title": attrs["translations"]["texts"]["title"],
        "department": attrs["translations"]["texts"]["organization"],
        "api_url": links["self"],
        "ad_url": links["ad_rendered"],
        "deadline": datetime.datetime.fromisoformat(attrs["dates"]["deadline"]),
        "cats": [cat["id"] for cat in rels["categories"]["data"]],
        "university": organizations[ int(rels["organization"]["data"]["id"]) ]["name"]
    }



######################################################################
# Format output
######################################################################

def format_job(job):
    uni = job["university"]
    deadline = job["deadline"]
    title = job["title"]
    url = job["ad_url"]

    return f"* {deadline.date().isoformat()}, {uni}, {title}, {url}"

######################################################################
# Retrieve jobs (file + web)
######################################################################

def extra_jobs():
    filename="extra_jobs.csv"
    print(f"Fetching jobs from '{filename}'.", file=sys.stderr)
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader( csvfile )
        for job in reader:
            publish = datetime.date.fromisoformat(job["publish"])
            deadline = datetime.date.fromisoformat(job["deadline"])
            today = datetime.date.today()
            if today >= publish and today <= deadline:
                yield { "deadline": datetime.datetime.combine(deadline,datetime.time.max),
                        "university": job["university"],
                        "title": job["title"],
                        "ad_url": job["url"] }

def scrape():
    jobs = list(extra_jobs()) + find_varbi_jobs()
    jobs = sorted(jobs, key=lambda d: d['deadline'].date())
    return jobs

if __name__ == "__main__":
    for job in scrape():
        print( format_job( job ) )
