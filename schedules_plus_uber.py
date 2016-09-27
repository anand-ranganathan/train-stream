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
import requests_toolbelt.adapters.appengine, requests


import jinja2
import webapp2
import pytz

from geopy.distance import vincenty
import csv
import mnr
import datetime

from rauth import OAuth2Service



JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]



# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second.


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
        
        orig_address= self.request.get("orig_address", "175 Atlantic St, Stamford, CT 06901")
        dest_address= self.request.get("dest_address", "10 N Water St, Norwalk, CT 06854")

        print "Code: " + self.request.get('code')
        
        parameters = {
            'redirect_uri': 'http://localhost:8080/schedules_plus_uber',
            'code': self.request.get('code'),
            'grant_type': 'authorization_code',
        }
        
        response = requests.post(
            'https://login.uber.com/oauth/token',
            auth=(
                'JeuCpIsCwA8uMuLSzLPbxv9CbMmUyo1h',
                'dwd8NSsL752ZeN8eQTqUj2tjHZjEzWzRpDZimrDH'
            ),
            data=parameters,
        )
        
        #### This access_token is what we'll use to make requests in the following
        #### steps
        access_token = response.json().get('access_token')
        print access_token
        
        url = 'https://api.uber.com/v1/me'
        response = requests.get(
            url,
            headers={
                'Authorization': 'Bearer %s' % access_token
            }
        )
        data = response.json()

        print data        

        print "PRODUCTS"

        url = 'https://api.uber.com/v1/products'
        lat, lon = self.city_2_lat_lon["stamford"]
        #params = {'latitude': '41.046805089379255', 'longitude': '-73.54195166628482'}
        params = {'latitude': lat, 'longitude': lon}

        response = requests.get(
            url,
            headers={
                'Authorization': 'Bearer %s' % access_token
            },
            params = params
                    
        )
        data_text = response.text        
        print data_text
        products = json.loads(data_text)
        
        print "PRICES"

        url = 'https://api.uber.com/v1/estimates/price'
        
        end_lat, end_lon = self.city_2_lat_lon["greenwich"]
        
        params = {'start_latitude': lat, 'start_longitude': lon,
                  'end_latitude': end_lat , 'end_longitude': end_lon }

        
#        params = {'start_latitude': '41.046805089379255', 'start_longitude': '-73.54195166628482',
#                  'end_latitute': '-41.10422679047199' , 'end_longitude': '73.40419656587348' }
        response = requests.get(
            url,
            headers={
                'Authorization': 'Bearer %s' % access_token
            },
            params = params                    
        )
        data_text = response.text        
        print data_text
        prices = json.loads(data_text)


        
        city_2_lat_lon = dict()
        with open('data/Railroad_Stations.csv', mode='r') as infile:
            reader = csv.reader(infile, delimiter =",")
            for rows in reader:
                if rows[5] != "LATITUDE":
                    city_2_lat_lon[rows[2].lower()] = (float(rows[5]), float(rows[4]))

        requests_toolbelt.adapters.appengine.monkeypatch()

        geocode_url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'sensor': 'false', 'address': orig_address}
        r = requests.get(geocode_url, params=params)
        results = r.json()['results']
        location = results[0]['geometry']['location']
        orig = (location['lat'], location['lng'])
        
        print orig

        params = {'sensor': 'false', 'address': dest_address}
        r = requests.get(geocode_url, params=params)
        results = r.json()['results']
        location = results[0]['geometry']['location']
        dest = (location['lat'], location['lng'])
        
        print dest
        
        orig_min = 1000000
        dest_min = 1000000
        nearest_orig = ""
        nearest_dest = ""
         
        for city, latlon in city_2_lat_lon.iteritems():
            orig_dist = vincenty(orig, latlon).miles
            if orig_min > orig_dist:
                nearest_orig = city
                orig_min = orig_dist
            dest_dist = vincenty(latlon, dest).miles
            if dest_min > dest_dist:
                nearest_dest = city
                dest_min = dest_dist
        
        
        station =  nearest_orig.lower()
        destination = nearest_dest.lower()       
        
        #station = self.request.get('station_name',
        #                                  "Stamford")

        #destination = self.request.get('destination_name',
        #                                  "Grand Central")
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

        template = JINJA_ENVIRONMENT.get_template('schedules_plus_uber.html')
        self.response.write(template.render(template_values))
# [END main_page]


# [START inputs]
class Inputs(webapp2.RequestHandler):

    def post(self):  
        station = self.request.get('orig_address',
                                          "166 Hubbard Ave, Stamford, CT")

        destination = self.request.get('dest_address',
                                          "10 N Water St, Norwalk, CT 06854")
        print station
        query_params = {'orig_address': station, 'dest_address': destination}
        self.redirect('/schedules_plus_uber?' + urllib.urlencode(query_params))
        
# [END inputs]


# [START main_page]
class UberSchedulesLogin(webapp2.RequestHandler):

    def get(self):  

        uber_api = OAuth2Service(
             client_id='JeuCpIsCwA8uMuLSzLPbxv9CbMmUyo1h',
             client_secret='dwd8NSsL752ZeN8eQTqUj2tjHZjEzWzRpDZimrDH',
             name='BetterOnTimeStamford',
             authorize_url='https://login.uber.com/oauth/authorize',
             access_token_url='https://login.uber.com/oauth/token',
             base_url='https://api.uber.com/v1/',
         )
        
        parameters = {
            'response_type': 'code',
        #    'redirect_uri': 'http://guestbook-143720.appspot.com/uber_logged_in',
            'redirect_uri': 'http://localhost:8080/schedules_plus_uber',
            'scope': 'profile',
        }
    
        #### Redirect user here to authorize your application
        login_url = uber_api.get_authorize_url(**parameters)
        print "about to redirect to "+login_url

        self.redirect(login_url)
             
# [END main_page]


# [START app]
app = webapp2.WSGIApplication([
    ('/schedules_plus_uber', MainPage),
    ('/address_input', Inputs),
    ('/schedules_plus_uber_login', UberSchedulesLogin)
    
], debug=True)
# [END app]
