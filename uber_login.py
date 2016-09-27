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
import json
import csv

import urllib
from geopy.distance import vincenty
from rauth import OAuth2Service
import requests, requests_toolbelt.adapters.appengine



JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

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

# [START Trains]
class Uber_Products:
    """Sub model for representing a train."""
    def __init__(self, capacity, description, display_name):   
        self.capacity = capacity
        self.description = description
        self.display_name = display_name
# [END Trains]


# [START Trains]
class Uber_Prices:
    """Sub model for representing a train."""
    def __init__(self, estimate, currency_code, display_name):   
        self.estimate = estimate
        self.currency_code = currency_code
        self.display_name = display_name
# [END Trains]



# [START main_page]
class UberLogin(webapp2.RequestHandler):

    def get(self):  

        uber_api = OAuth2Service(
             client_id='***',
             client_secret='***',
             name='***',
             authorize_url='https://login.uber.com/oauth/authorize',
             access_token_url='https://login.uber.com/oauth/token',
             base_url='https://api.uber.com/v1/',
         )
        
        parameters = {
            'response_type': 'code',
        #    'redirect_uri': 'http://guestbook-143720.appspot.com/uber_logged_in',
            'redirect_uri': 'http://localhost:8080/uber_logged_in',
            'scope': 'profile',
        }
    
        #### Redirect user here to authorize your application
        login_url = uber_api.get_authorize_url(**parameters)
        print "about to redirect to "+login_url

        self.redirect(login_url)
             
# [END main_page]


# [START inputs]
class UberLoggedIn(webapp2.RequestHandler):
    

    def get(self):  
        #### Once your user has signed in using the previous step you should redirect
        #### them here
        city_2_lat_lon = dict()
        with open('data/Railroad_Stations.csv', mode='r') as infile:
            reader = csv.reader(infile, delimiter =",")
            for rows in reader:
                if rows[5] != "LATITUDE":
                    city_2_lat_lon[rows[2].lower()] = (float(rows[5]), float(rows[4]))

        requests_toolbelt.adapters.appengine.monkeypatch()
        
        print "Code: " + self.request.get('code')
        code = self.request.get('code')
        parameters = {
            'redirect_uri': 'http://localhost:8080/uber_logged_in',
            'code': code,
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
        
        orig_address= self.request.get("orig_address", "175 Atlantic St, Stamford, CT 06901")
        dest_address= self.request.get("dest_address", "10 N Water St, Norwalk, CT 06854")

        
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

        print "PRODUCTS"
        orig_lat, orig_lon = orig
        dest_lat, dest_lon = dest

        url = 'https://api.uber.com/v1/products'
        #params = {'latitude': '41.046805089379255', 'longitude': '-73.54195166628482'}
        params = {'latitude': orig_lat, 'longitude': orig_lon}

        response = requests.get(
            url,
            headers={
                'Authorization': 'Bearer %s' % access_token
            },
            params = params
                    
        )
        data_text = response.text        
        print data_text
        direct_products = json.loads(data_text)        

        orig_station_lat, orig_station_lon = city_2_lat_lon[nearest_orig]
        dest_station_lat, dest_station_lon = city_2_lat_lon[nearest_dest]
        #params = {'latitude': '41.046805089379255', 'longitude': '-73.54195166628482'}
        params = {'latitude': dest_station_lat, 'longitude': dest_station_lon}

        response = requests.get(
            url,
            headers={
                'Authorization': 'Bearer %s' % access_token
            },
            params = params
                    
        )
        data_text = response.text        
        print data_text
        dest_products = json.loads(data_text)        

        print "TIMES"

        url = 'https://api.uber.com/v1/estimates/time'
        #params = {'latitude': '41.046805089379255', 'longitude': '-73.54195166628482'}
        params = {'start_latitude': orig_lat, 'start_longitude': orig_lon}

        response = requests.get(
            url,
            headers={
                'Authorization': 'Bearer %s' % access_token
            },
            params = params
                    
        )
        data_text = response.text        
        print data_text
        direct_times = json.loads(data_text)        

        #params = {'latitude': '41.046805089379255', 'longitude': '-73.54195166628482'}
        params = {'start_latitude': dest_station_lat, 'start_longitude': dest_station_lon}

        response = requests.get(
            url,
            headers={
                'Authorization': 'Bearer %s' % access_token
            },
            params = params
                    
        )
        data_text = response.text        
        print data_text
        dest_times = json.loads(data_text)        



        
        print "PRICES"

        url = 'https://api.uber.com/v1/estimates/price'
        
        
        params = {'start_latitude': orig_lat, 'start_longitude': orig_lon,
                  'end_latitude': dest_lat , 'end_longitude': dest_lon }

        
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
        direct_prices = json.loads(data_text)

        params = {'start_latitude': orig_lat, 'start_longitude': orig_lon,
                  'end_latitude': orig_station_lat , 'end_longitude': orig_station_lon }
        
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
        orig_prices = json.loads(data_text)

        params = {'start_latitude': dest_station_lat, 'start_longitude': dest_station_lon,
                  'end_latitude': dest_lat , 'end_longitude': dest_lon }
        
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
        dest_prices = json.loads(data_text)

        combined_price_low = int(orig_prices["prices"][0]["low_estimate"]) + int(dest_prices["prices"][0]["low_estimate"]) + 4
        combined_price_high = int(orig_prices["prices"][0]["high_estimate"]) + int(dest_prices["prices"][0]["high_estimate"]) + 4

        template_values = {
            'orig_address' : orig_address,
            'dest_address'  : dest_address,
            'current_time' : format(datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%l:%M %p')),
            'station': station,
            'destination': destination,
            'trains': trains,
            'code': code,
            'uber_direct_products' : direct_products,
            'uber_direct_prices' : direct_prices,
            'uber_orig_prices' : orig_prices,
            'uber_dest_products' : dest_products,
            'uber_dest_prices' : dest_prices,
            'combined_price_low': combined_price_low,
            'combined_price_high': combined_price_high,
            'direct_times': direct_times,
            'dest_times': dest_times,
            'orig_lat': orig_lat, 
            'orig_lon': orig_lon,
            'dest_lat': dest_lat , 
            'dest_lon': dest_lon,
            'orig_station_lat': orig_station_lat, 
            'orig_station_lon' : orig_station_lon,
            'dest_station_lat' : dest_station_lat, 
            'dest_station_lon' : dest_station_lon
        
        }

        template = JINJA_ENVIRONMENT.get_template('schedules_plus_uber.html')
        self.response.write(template.render(template_values))


# [END inputs]

# [START inputs]
class Inputs(webapp2.RequestHandler):

    def post(self):  
        station = self.request.get('orig_address',
                                          "166 Hubbard Ave, Stamford, CT")

        destination = self.request.get('dest_address',
                                          "10 N Water St, Norwalk, CT 06854")
        
        code = self.request.get('code')
        
        print station
        query_params = {'orig_address': station, 'dest_address': destination, 'code': code}
        self.redirect('/uber_logged_in?' + urllib.urlencode(query_params))
        
# [END inputs]



# [START app]
app = webapp2.WSGIApplication([
    ('/uber_login', UberLogin),
    ('/uber_logged_in', UberLoggedIn),
    ('/address_input', Inputs),
], debug=True)
# [END app]
