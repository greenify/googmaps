#!/usr/bin/env python
import sys
import requests
import re
import simplejson
from optparse import OptionParser
from termcolor import colored, cprint
from time import mktime
import parsedatetime.parsedatetime as pdt
import urllib2
import time

cal = pdt.Calendar()

def main():
  args = sys.argv

  parser = OptionParser()
  usage = "usage: %prog [options] origin destination"
  parser = OptionParser(usage=usage)
  # see https://developers.google.com/maps/documentation/directions/
  parser.add_option("-m", "--mode", action="store", dest="mode", help="specifies type of transportation desired [driving,transit,bicycling,walking]", default="driving")
  parser.add_option("-u", "--units", action="store", dest="units", help="specifies choice between metric and imperial systems")
  parser.add_option("-z", "--no-url", action="store_true", dest="nourl", default=False, help="Disables URL-String")
  parser.add_option("-s", "--sensor", action="store", dest="sensor", default="false")
  parser.add_option("-a", "--arrival", action="store", dest="arrival_time", help="specifies desired time of arrival. can be stated in natural language")
  parser.add_option("-d", "--departure", action="store", dest="departure_time", help="specifies desired time of departure. can be stated in natural language")
  parser.add_option("-e", "--evade", action="store", dest="avoid", help="specifies choice in avoiding tolls or highways")
  parser.add_option("-r", "--region", action="store", dest="region", help="Region bias. Set tld")
  parser.add_option("-i", "--iterator", action="store", dest="iterator", help="how many times should the query be iterated?")

# probably we should use alternatives instead of iterating ourselves

  (options, args) = parser.parse_args(args)
  if len(args) != 3:
    parser.error("Incorrect number")

  ites =0
  try:
      ites = int(options.iterator)
  except ( ValueError,AttributeError, TypeError) as e:
      ites = 0
  except Exception, e:
      raise e

  # check whether to use iterator
  if ites == 0:
     make_url(parser, options, args)
  else:
     for i in range(ites):
        newOffset = make_url(parser, options, args, False)

        options =increment_time(options, newOffset)

def make_url(parser, options, args, printInfo=True):
  checkinput(options)

  url_end = ''

  for key,value in options.__dict__.items():
    if(value != None):
      if key in ["departure_time", "arrival_time"]:
          try:
            value = int(value)
          except ValueError as e:
            value = int(mktime(cal.parse(value)[0]))
          finally:
              time = value
              value = str(value)
      if not isinstance(value, bool):
        re.sub(' ', '+', value)
        url_end += key + '=' + value + '&'

  origin = re.sub(' ', '+', args[1])
  destination = re.sub(' ', '+', args[2])

  if not options.nourl :
       cprint ("To view these directions online, follow this link: " + "http://mapof.it/" + origin + '/' + destination, 'cyan')

  base_url = 'http://maps.googleapis.com/maps/api/directions/json?origin=' + origin + '&destination=' + destination + '&'

  url = (base_url + url_end)[:-1]
  while True:
     val =print_path(url,printInfo)
     if val > 0:
       return val

def increment_time(options,valueNew, inc=5):
  for key,value in options.__dict__.items():
    if(value != None):
      if key in ["departure_time", "arrival_time"]:
        value = int(mktime(cal.parse(value)[0]))
        # do increment
        value = valueNew + 60 ;
        options.__dict__[key] = str( value)
        return options

def print_path(url, printInfo=True):

  req = urllib2.Request(url)
  response = urllib2.urlopen(req)
  resp_text = response.read()
  respjson= simplejson.loads(resp_text)

  if respjson['status'] == 'OVER_QUERY_LIMIT' :
        print "QUERY_OVERLIMIT"
        time.sleep(1)
        return -1;

  checkresp(respjson, response)

  keypoints = respjson['routes'][0]['legs'][0]

  if printInfo:
    print "From: " + keypoints['start_address']
    print "To: " + keypoints['end_address']
    print "Distance: " + keypoints['distance']['text']
    print "Duration: " + keypoints['duration']['text']

  printwarnings(respjson)

  if 'mode=transit' in url:
    cprint( keypoints['departure_time']['text'], 'blue', end='')
    sys.stdout.write("\t- ")
    cprint( keypoints['arrival_time']['text'], 'blue')

  steps, linenum = keypoints['steps'], 1
  for step in steps:
    instruction = sanitize(step['html_instructions'])
    #fix for formatting issue on last line of instructions
    instruction = re.sub('Destination', '. Destination', instruction)
    sys.stdout.write(str(linenum) + '. ' + instruction + ': ')
    cprint(step['duration']['text'], 'green')
    linenum += 1

  return keypoints['departure_time']['value']

def sanitize(sentence):
  result = re.sub('<.*?>', '', sentence.encode('ascii', 'ignore'))
  return result


def checkinput(options):
  if(options.mode == "transit" and not (options.departure_time or options.arrival_time)):
    parser.error("Can't specify transit without either arrival or departure time")
  elif options.avoid not in ["tolls", "highways", None]:
      parser.error("Must specify either tolls or highways to evade")


def checkresp(respjson, resp):
  if resp.code != 200:
    print "Sorry, something went wrong. Here is the output:"
    print resp.text
    sys.exit()
  elif respjson['status'] == "ZERO_RESULTS":
      print "Your query returned no results. Try ^ that link maybe?"
      sys.exit()

  try:
    respjson['routes']
  except KeyError:
    print "No 'routes' in response"

  try:
    respjson['routes'][0]
  except IndexError:
    print "Index out of range"
  except TypeError:
    print "Bad index type"

  try:
    respjson['routes'][0]['legs']
  except KeyError:
    print "Bad Key"


def printwarnings(respjson):
  warnings = respjson['routes'][0]['warnings']
  if warnings:
      # remove warning for pedestrians, its annoying
      if len(warnings) == 1 and "pedestrian" in  warnings[0]:
        pass
      else:
         cprint ("\nWarnings:", 'red')
         for warning in warnings:
           cprint ("- " + sanitize(warning), 'red')


main()
