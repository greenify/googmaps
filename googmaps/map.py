#!/usr/bin/env python
import sys, requests, re, simplejson
from optparse import OptionParser
from getpath import make_url
from printpath import print_path
from termcolor import colored, cprint
from time import mktime
import parsedatetime.parsedatetime as pdt

def main():
  args = sys.argv

  parser = OptionParser()
  usage = "usage: %prog [options] origin destination"
  parser = OptionParser(usage=usage)
  parser.add_option("-m", "--mode", action="store", dest="mode", help="specifies type of transportation desired", default="driving")
  parser.add_option("-u", "--units", action="store", dest="units", help="specifies choice between metric and imperial systems")
  parser.add_option("-s", "--sensor", action="store", dest="sensor", default="false")
  parser.add_option("-a", "--arrival", action="store", dest="arrival_time", help="specifies desired time of arrival. can be stated in natural language")
  parser.add_option("-d", "--departure", action="store", dest="departure_time", help="specifies desired time of departure. can be stated in natural language")
  parser.add_option("-e", "--evade", action="store", dest="avoid", help="specifies choice in avoiding tolls or highways")

  (options, args) = parser.parse_args(args)
  if len(args) != 3:
    parser.error("Incorrect number")
  make_url(parser, options, args)

def make_url(parser, options, args):
  url_end = ''

  if(options.mode == "transit" and not (options.departure_time or options.arrival_time)):
    parser.error("Can't specify transit without either arrival or departure time")
  else:
    if options.avoid not in ["tolls", "highways", None]:
      parser.error("Must specify either tolls or highways to evade")

  cal = pdt.Calendar()

  for key,value in options.__dict__.items():
    if(value != None):
      if key in ["departure_time", "arrival_time"]:
        value = str(int(mktime(cal.parse(value)[0])))
      re.sub(' ', '+', value)
      url_end += key + '=' + value + '&'
  
  origin = re.sub(' ', '+', args[1]) 
  destination = re.sub(' ', '+', args[2])

  cprint ("To view these directions online, follow this link: " + "http://mapof.it/" + origin + '/' + destination, 'cyan')

  base_url = 'http://maps.googleapis.com/maps/api/directions/json?origin=' + origin + '&destination=' + destination + '&'
  
  url = (base_url + url_end)[:-1]
  print_path(url)

def sanitize(sentence):
  result = re.sub('<.*?>', '', sentence.encode('ascii', 'ignore'))
  return result

def print_path(url):
  resp = requests.get(url)
  myjson= simplejson.loads(resp.text)

  if resp.status_code != 200: 
    print "Sorry, something went wrong"
    sys.exit()
  else:
    if myjson['status'] == "ZERO_RESULTS":
      print "Your query returned no results"
      sys.exit()

  keypoints = myjson['routes'][0]['legs'][0]

  print "From: " + keypoints['start_address']
  print "To: " + keypoints['end_address']
  print "Distance: " + keypoints['distance']['text']
  print "Duration: " + keypoints['duration']['text'] 

  warnings = myjson['routes'][0]['warnings']
  if warnings:
    cprint ("\nWarnings:", 'red')
    for warning in warnings:
      cprint ("- " + sanitize(warning), 'red')

  print "\n"
  
  steps, linenum = keypoints['steps'], 1
  for step in steps:
    instruction = sanitize(step['html_instructions'])
    #fix for formatting issue on last line of instructions
    instruction = re.sub('Destination', '. Destination', instruction)
    sys.stdout.write(str(linenum) + '. ' + instruction + ': ') 
    cprint(step['duration']['text'], 'green')
    linenum += 1

  #TODO: add shit for how long peeps is gonna wait at each stop for transit

main()