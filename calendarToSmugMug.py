#!/usr/bin/env python


# Uses SmugMug API 1.3.0
# https://api.smugmug.com/services/api/?version=1.3.0
#
from __future__ import print_function
from smugpy import SmugMug
import sys, io, json
import os.path

import collections
import urllib.request
import datetime
from operator import attrgetter
from collections import OrderedDict

import icalendar
import SmugMugOAuth

# This is the iCal feed for the VHS Band Calendar from which the events data is
# read.
CHARMS_URL = 'https://www.charmsoffice.com/charms/calsync.asp?s=VandegriftHSBand'

EVENTS_FILE = 'event_list.txt'
ACCESS_TOKEN_FILE = 'smugmug_access_token.json'

# Our whitelist words. The program will filter based on presence of these words
# in the summary string. If you want the event picked up by the program then add
# the keyword to this list.
#
KEYWORDS = [
    'football', 'party', 'marching', 'contest', 'tmea', 'region', 'concert',
    'banquet', 'march-a-thon!', 'spring trip'
    ]

def write_events_to_file(sorted_unique_events):
    """ Formats and writes the event date and summary to EVENTS_FILE """

    output_file = open(EVENTS_FILE, "w")
    output_file.truncate()

    for event in sorted_unique_events:
        line = event.event_date.strftime('%Y-%m-%d') + ' ' + event.summary.title() + '\n'
        output_file.write(line)

    output_file.close()

def save_access_token(access_token):
    """ Save the access token to a local file """
    with open(ACCESS_TOKEN_FILE, 'w') as output_file:
        json.dump(access_token, output_file, sort_keys=True, indent=4, ensure_ascii=False)

    output_file.close()

def get_access_token_from_file():
    """ Get the access token that is saved to file """
    with open(ACCESS_TOKEN_FILE) as data_file:
        access_token = json.load(data_file)

    return access_token

def make_unique_event_list(event_list):
    """ Given a list of events with possible multiple events, return a list
    that is unique on the summary field """
    seen_events = set()
    unique_events = []
    for event in event_list:
        if event[1] not in seen_events:
            unique_events.append(event)
            seen_events.add(event[1])

    return unique_events

# This function gets the calendar data from the specified URL.
# It supports the iCal format.
#
def request_calendar():
    """ Gets the results from the VHS Band Charms Calendar feed """
    req = urllib.request.Request(CHARMS_URL)

    response = urllib.request.urlopen(req)
    data = response.read()

    raw_calendar = icalendar.cal.Calendar.from_ical(data)

    event_tuple = collections.namedtuple('event_tuple', 'event_date, summary')
    events = []

    for event in raw_calendar.walk('VEVENT'):

        # Get the date an normalize to datetime.date format
        decoded_date = event.decoded('dtstart')
        if isinstance(decoded_date, datetime.datetime):
            event_date = decoded_date.date()
        else:
            event_date = decoded_date

        # create a uniform lowercase string for searching
        summary = (event.decoded('summary'))
        summary_str = summary.decode("utf-8").lower()

        # strip anything after the first '(' to end-of-line
        summary_str = summary_str.split('(')[0]

        # strip anything after the first '-' to end-of-line
        summary_str = summary_str.split('-')[0]

        # select only events that have a word from KEYWORDS
        # in the summary field
        if any(w in summary_str for w in KEYWORDS):
            record = event_tuple(event_date, summary_str)
            events.append(record)

    return events


def list_user_albums(smugmug, access_token):
    """ convenience routine for listing the user's SmugMug public albums """
    albums = smugmug.albums_get(NickName=access_token['User']['NickName'])
    for album in albums["Albums"]:
        print("%s, %s, %s" % (album["id"], album['Key'], album["Title"]))

#
# Main
#
def main():

    # event_list has the fields: event_date, summary
    #
    event_list = request_calendar()

    # Prune duplicate events that span multiple dates
    #
    unique_events = make_unique_event_list(event_list)

    # This sorts all the unique events by date because unique_events lose their original order
    #
    sorted_unique_events = sorted(unique_events, key=attrgetter('event_date'))

    # Capture the unique events list to a disk file
    write_events_to_file(sorted_unique_events)

    #sys.exit()

    #
    # OAuth 1.0 authorization
    #
    # Steps 1 and 2 will get an unsecured token and URL, which is listed to
    # console. Cut and paste the URL you get on the screen into the browser
    # to authorize this transaction.
    #

    if os.path.isfile(ACCESS_TOKEN_FILE):
        print('Using found access token file')
        access_token = get_access_token_from_file()
    else:
        # Step 1: get request token and authorization URL:
        (url, requestToken) = SmugMugOAuth.smugmugOauthRequestToken()

        # Step 2: "visit" the authorization URL:
        SmugMugOAuth.userAuthorizeAtSmugmug(url)

        # Step 3: Upgrade the authorized request token into an access token
        access_token = SmugMugOAuth.smugmugOauthGetAccessToken(requestToken)

        save_access_token(access_token)

    # Step 3.5: You should save off the access_token so you can resume at
    # the following step from now on.  There is no need to jump through
    # the request token and authorization URL more than once.
    # TODO - Implement saving the access token

    # Step 4 (and step 1 in the future): log in with the (saved) access
    # token to get an authorized connection to smugmug.com:

    smugmug = SmugMugOAuth.smugmugOauthUseAccessToken(access_token)

    #
    # KEEP THIS CODE - Use it to discover folder key values
    #
    # categories = smugmug.categories_get(NickName=access_token['User']['NickName'])
    # for category in categories["Categories"]:
    #     print("%s, %s, %s" % (category["id"], category['Name'], category["NiceName"]))

    # sys.exit()

    # TODO - Read the events file rather than processing the internal data.
    
    upload_key = 'vipers'
    football_game_category_id = '11924665524'   # Insert real VHS BAND Ids here
    event_category_id = '5530913789'            # and here

    for e in sorted_unique_events:
        # Create a forlder name in the form "YY-MM-DD Event Title" (first letter capitalized)
        #
        folder_title = e.event_date.strftime('%Y-%m-%d') + " " + e.summary.title()

        # Set the category (folder) in which the galleries are created. 
        # TODO - Expand logic to add other folders.
        #
        if 'football game' in e.summary:
            folder_category_id = football_game_category_id
        else:
            folder_category_id = event_category_id

        # Create an album under the Games folder
        album = smugmug.albums_create(Title=folder_title,
                                      CategoryID=folder_category_id,
                                      UploadKey=upload_key)

        print("Key: %s, Title: %s" % (album['Album']['Key'], folder_title))
        print("URL: https://naderaskari.smugmug.com/upload/%s/%s" % (album['Album']['Key'], upload_key))

if __name__ == '__main__':
    main()