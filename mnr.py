#!/usr/bin/env python

"""
mnr.py: Quick CLI interface with MTA-Metro North Train Time
"""

import os, sys, datetime, requests
import requests_toolbelt.adapters.appengine
from lxml import html
from collections import namedtuple
#from google.appengine.api import urlfetch

class Travel:
  Schedule = namedtuple('Schedule', 'dtime destination track status stops_list')

  def __init__(self, station='Grand Central Terminal', destination=None):
    # initialize a http session for cookie mgmt
    # Use the App Engine Requests adapter. This makes sure that Requests uses
    # URLFetch.
    requests_toolbelt.adapters.appengine.monkeypatch()
    self.session = requests.Session()

    # load our list of stations from mta.info
    self._stations = {}
    self.load_stations()

    # set our starting and ending stations
    # default to Grand Central, if start isn't specified
    station = station or 'Grand Central Terminal'
    self._destination = destination

    # try to find our starting station in the list returned by mta.info
    if station in self._stations.keys():
      self._station = self._stations[station]
    else:
      for s in self._stations.keys():
        if station.lower() in s.lower():
          self._station = self._stations[s]
          break

  def load_stations(self):
    # grab list
    r = self.session.get('http://as0.mta.info/mnr/mstations/default.cfm')

    # parse html
    doc = html.fromstring(r.text)

    # use xpath to find all station options
    for option in doc.xpath('//select[@name="P_AVIS_ID"]/option'):
      idx, name = option.attrib.get('value').split(',', 2)
      self._stations[name] = { 'idx': idx, 'name': name }

  def station(self):
    # return a title-capitalized version of the starting station name
    return self._station['name'].title()

  def schedule(self):
    # get time+track information from mta.info for given station
    r = self.session.post('http://as0.mta.info/mnr/mstations/station_status_display.cfm', data={
      'P_AVIS_ID': '{},{}'.format(self._station['idx'], self._station['name']),
      'Get Train Status': 'Get Train Status',
      'refered': 'ault.cfm'
    })

    # parse html returned from mta.info
    scheduled = []
    
    doc = html.fromstring(r.text)

    # loop through each result row
    for row in doc.xpath('//table/tr'):
      inputs = row.xpath('form/td/input')
      stops_list = list()
      for i in inputs:
          name = i.get("name")
          value = i.get("value")
          if name == "stops_list":
              stops_list = value.split(",")
              stops_list_lower = [x.lower() for x in stops_list]

      cols = row.xpath('td')
      
      # filter out first header row
      if cols[0].text == 'Scheduled Time':
        continue

      # if user has specified a destination, filter out trains that don't match
      #if self._destination is not None and self._destination.lower() not in cols[1].text.lower():
      if self._destination is not None and self._destination.lower() not in stops_list_lower:
        continue
      
      # filter out trains making their last stop
      if self._station['name'].lower() == cols[1].text.lower():
        continue
    
      # add this train+track to scheduled departure list
      scheduled.append(Travel.Schedule(dtime=cols[0].text, 
                                       destination=cols[1].text, 
                                       track=cols[2].text, 
                                       status=cols[3].text, 
                                       stops_list=",".join(stops_list)))

    return scheduled
  
def main(argv=None):
  if argv is None:
    argv = sys.argv
  args = argv[1:]

  t = None
  if len(args) <= 0:
    t = Travel()
  else:
    if args[0] == 'from':
      args.pop(0)

    to = None
    station = None
    destination = None
    if 'to' in args:
      to = args.index('to')
      args.pop(to)

      if to == 0:
        station = None
        destination = ' '.join(args)
      else:
        station = ' '.join(args[0:to])
        destination = ' '.join(args[to:])
    else:
      station = ' '.join(args)

    t = Travel(station=station, destination=destination)

  print '\n*** {} ***\n'.format(datetime.datetime.now().strftime('%l:%M %p'))
  print 'Leaving from {}'.format(t.station())

  print '\nScheduled Trains'
  print '----------------'

  for schedule in t.schedule():
    if len(schedule.track.replace(' ', '')) == 0:
      track = '(no track yet)'
    else:
      track = 'Track {}'.format(schedule.track)

    print '{}\tTo {}\t{}\t{}'.format(schedule.dtime, schedule.destination.ljust(20), track.ljust(10), schedule.status)
  print

  return 0

if __name__ == '__main__':
  sys.exit(main())

