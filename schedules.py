#!/usr/bin/env python

# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START imports]
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2
import pytz

import mnr
import datetime

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

DEFAULT_GUESTBOOK_NAME = 'default_guestbook'


# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second.

def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity.

    We use guestbook_name as the key.
    """
    return ndb.Key('Guestbook', guestbook_name)


# [START Trains]
class Train:
    """Sub model for representing a train."""
    def __init__(self, deptime, destination, track, status, stops_list):   
        self.deptime = deptime
        self.destination = destination
        self.track = track
        self.status = status
        self.stops_list = stops_list
# [END Trains]


# [START main_page]
class MainPage(webapp2.RequestHandler):

    def get(self):   
        to = None        
        station = None
        destination = None
        station = self.request.get('station_name',
                                          "Stamford")

        destination = self.request.get('destination_name',
                                          "Grand Central")
        t = mnr.Travel(station=station, destination=destination)

        trains = list()

        for schedule in t.schedule():
            if len(schedule.track.replace(' ', '')) == 0:
              track = '(no track yet)'
            else:
              track = 'Track {}'.format(schedule.track)
        
            trains.append(Train(schedule.dtime, schedule.destination, track, schedule.status, schedule.stops_list))

        print trains

        template_values = {
            'current_time' : format(datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%l:%M %p')),
            'station': station,
            'destination': destination,
            'trains': trains,
        }

        template = JINJA_ENVIRONMENT.get_template('schedules.html')
        self.response.write(template.render(template_values))
# [END main_page]


# [START inputs]
class Inputs(webapp2.RequestHandler):

    def post(self):  
        station = self.request.get('station_name',
                                          "Stamford")

        destination = self.request.get('destination_name',
                                          "Grand Central")
        print station
        query_params = {'station_name': station, 'destination_name': destination}
        self.redirect('/schedules?' + urllib.urlencode(query_params))
        
# [END inputs]


# [START app]
app = webapp2.WSGIApplication([
    ('/schedules', MainPage),
    ('/station_input', Inputs)
], debug=True)
# [END app]
