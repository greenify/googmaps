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
import texttable
import textwrap
import gettext
import os
import locale

#i18n
# Change this variable to your app name!
#  The translation files will be under
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
APP_NAME = "GooGmaps"
APP_DIR = os.path.dirname(os.path.realpath(__file__))
# This is ok for maemo. Not sure in a regular desktop:
#APP_DIR = os.path.join (sys.prefix, 'share')
LOCALE_DIR = os.path.join(APP_DIR, 'i18n') # .mo files will then be located in APP_Dir/i18n/LANGUAGECODE/LC_MESSAGES/
 
# Now we need to choose the language. We will provide a list, and gettext
# will use the first translation available in the list
#
#  In maemo it is in the LANG environment variable
#  (on desktop is usually LANGUAGES)
DEFAULT_LANGUAGES = os.environ.get('LANG', '').split(':')
DEFAULT_LANGUAGES += ['en_US']
 
lc, encoding = locale.getdefaultlocale()
if lc:
    languages = [lc]
 
# Concat all languages (env + default locale),
#  and here we have the languages and location of the translations
languages += DEFAULT_LANGUAGES
mo_location = LOCALE_DIR
 
# Lets tell those details to gettext
#  (nothing to change here for you)
gettext.install(True, localedir=None, unicode=1)
gettext.find(APP_NAME, mo_location)
gettext.textdomain (APP_NAME)
gettext.bind_textdomain_codeset(APP_NAME, "UTF-8")


language = gettext.translation(APP_NAME, mo_location, languages, fallback=True)
language.install()

# how to i18n
# 1. create .po: xgettext --language=Python --keyword=_ --output=i18n/po/GooGmaps.pot `find . -name "*.py"`
# 2. create several po for each language: msginit --input=mussorgsky.pot --locale=de_DE
#     change ASCII to UTF-8
# 3. compile translation:  msgfmt i18n/po/de.po --output-file i18n/de/LC_MESSAGES/GooGmaps.mo

cal = pdt.Calendar()


def main():
	args = sys.argv

	parser = OptionParser()
	usage = "usage: %prog [options] origin destination"
	parser = OptionParser(usage=usage)
	# see https://developers.google.com/maps/documentation/directions/
	parser.add_option("-m", "--mode", action="store", dest="mode",
					help="specifies type of transportation desired [driving,transit,bicycling,walking]", default="driving")
	parser.add_option("-u", "--units", action="store", dest="units",default="metric",
					help="specifies choice between metric and imperial systems")
	parser.add_option("-z", "--no-url", action="store_true",
					dest="nourl", default=False, help="Disables URL-String")
	parser.add_option("-s", "--sensor", action="store",
					dest="sensor", default="false")
	parser.add_option("-a", "--arrival", action="store", dest="arrival_time",
					help="specifies desired time of arrival. can be stated in natural language")
	parser.add_option("-d", "--departure",default="now", action="store", dest="departure_time",
					help="specifies desired time of departure. can be stated in natural language")
	parser.add_option("-e", "--evade", action="store", dest="avoid",
					help="specifies choice in avoiding tolls or highways")
	parser.add_option("-c", "--width", action="store", default=80, dest="width",
					help="output width")
	parser.add_option("-l", "--language", action="store",
					dest="language", default="", help="Direction language.")
	parser.add_option("-r", "--region", action="store",
					dest="region", help="Region bias. Set tld")
	parser.add_option("-i", "--iterator", action="store",
					dest="iterator", help="Number of results to be retrieved")

	# probably we should use alternatives instead of iterating ourselves

	(options, args) = parser.parse_args(args)
	if len(args) != 3:
	 	parser.error(_("Incorrect number"))

	# check for language
	if True:

		language = gettext.translation(APP_NAME, mo_location, [options.language], fallback=True)
		language.install()

	ites = 0
	try:
	  ites = int(options.iterator)
	except (ValueError, AttributeError, TypeError) as e:
	  ites = 0
	except Exception as e:
	  raise e

	# check whether to use iterator

	if ites == 0:
		make_url(parser, options, args)
	else:
		if options.mode != "transit":
			cprint(_("iterating does not make sense"), "red")
			make_url(parser, options, args)
		else:
			for i in range(ites):
				newOffset = make_url(parser, options, args, False)
				options = increment_time(options, newOffset)


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

			if not (isinstance(value, bool) or isinstance(value, int)):
				re.sub(' ', '+', value)
				url_end += key + '=' + value + '&'

	origin = re.sub(' ', '+', args[1])
	destination = re.sub(' ', '+', args[2])

	if not options.nourl :
		cprint (_("To view these directions online, follow this link: ") + "http://mapof.it/" + origin + '/' + destination, 'cyan')

	base_url = 'http://maps.googleapis.com/maps/api/directions/json?origin=' + origin + '&destination=' + destination + '&'

	url = (base_url + url_end)[:-1]
	while True:
		val =print_path(url,printInfo,options.mode , int(options.width))
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
				break
	return options

def print_path(url, printInfo=True, mode="car", width=120):

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
		print _("From") +": " + keypoints['start_address']
		print _("To")+": " + keypoints['end_address']
		print _("Distance")+": " + keypoints['distance']['text']
		print _("Duration")+": " + keypoints['duration']['text']

	printwarnings(respjson, width)

	if 'mode=transit' in url:
		cprint( keypoints['departure_time']['text'], 'blue', end='')
		sys.stdout.write("\t- ")
		sys.stdout.write(colored( keypoints['arrival_time']['text'], 'blue'))
		# we want to format the duration by ourself
		if not printInfo:
			sys.stdout.write(" [")
			duraText= keypoints['duration']['text'].split(" ")
			rem = ""

			# hack for german abbreviations
			for dur in duraText:
				if dur in "Minuten":
					dur = "Mins."

			rem =""
			if len(duraText) > 2:
				rem = " "+ " ".join(duraText[2:])
			else:
				duraText[1] = " "+ duraText[1]
			duraText=  "%-2s%s%s" % (duraText[0] , duraText[1], rem)
			sys.stdout.write(colored(duraText, "blue"))
			sys.stdout.write("]")
		print ""

	steps, linenum = keypoints['steps'], 1


	table = texttable.Texttable()
	table.set_deco(0)
	table.set_cols_dtype(['t',  't',    't']) 
	table.set_cols_align(["l", "l", "l"])
	table.set_cols_valign(["t", "t", "t"])
	#dirty hack
	width = width + 7
	instruction_width = width -4 -20
	table.set_cols_width([4,instruction_width, 21])
	

	for step in steps:
		instruction = sanitize(step['html_instructions'], instruction_width-10)
		# fix for formatting issue on last line of instructions
		instruction = re.sub('Destination', '. Destination', instruction)

		duraText= step['duration']['text'].split(" ")
		# hack for german abbreviations
		for i in range(len(duraText)):
			if "Minuten" in duraText[i]:
				duraText[i] = "Mins."
		rem = ""
		if len(duraText) > 2:
				rem = " " +" ".join(duraText[2:])
		duraText=  " %-2s %s%s" % (duraText[0] , duraText[1], rem)
		duraText = apply_color_per_chunk(duraText, 'green')

	
		table.add_row([str(linenum)+".",instruction, duraText])
		linenum += 1

	print table.draw()

	if mode == "transit":
		return keypoints['departure_time']['value']
	else:
		return 1;

def sanitize(sentence, length=80):

	# remove all divs
	result = re.sub('<div([^<]*)>([^<]*)</div>', '\n\g<2>', sentence.encode('utf-8'))
	# double continue hack
	#result = re.sub('>Continue to (.*)$', '> -> \g<1>', result);

	out= ""
	bolded = result.split("<b>")
	for bolder in bolded:
		tBolder = bolder.split("</b>")
		# only applc bold effect if it'<b>
		if len( tBolder) > 1:
			cBolder = apply_color_per_chunk(tBolder[0], attr=['bold'])
			out += cBolder + tBolder[1]
		else:
			out += bolder

	result =out
	# remove remaining tags
	result = re.sub('<.*?>', '', result)
	return result

def apply_color_per_chunk(line, color='', attr=[]):
	out = ""
	chunk = line.split(" ")
	i = 0
	for res in chunk:
		if color:
			out += colored(res, color,attrs=attr)
		else:
			out += colored(res, attrs=attr)
		if i < len(chunk) -1:
			out += " "
		i = i+1

	return out

def checkinput(options):
	if(options.mode == "transit" and not (options.departure_time or options.arrival_time)):
		parser.error("Can't specify transit without either arrival or departure time")
	elif options.avoid not in ["tolls", "highways", None]:
	  parser.error("Must specify either tolls or highways to evade")


def checkresp(respjson, resp):
	if resp.code != 200:
		print _("Sorry, something went wrong. Here is the output:")
		print resp.text
		sys.exit()
	elif respjson['status'] == "ZERO_RESULTS":
		print _("Your query returned no results. Try ^ that link maybe?")
		sys.exit()

		try:
		  respjson['routes']
		except KeyError:
		  print _("No 'routes' in response")

		try:
		  respjson['routes'][0]
		except IndexError:
		  print _("Index out of range")
		except TypeError:
		  print _("Bad index type")

		try:
		  respjson['routes'][0]['legs']
		except KeyError:
		  print _("Bad Key")


def printwarnings(respjson, cwidth):
	warnings = respjson['routes'][0]['warnings']
	if warnings:
	  # remove warning for pedestrians, its annoying
		if len(warnings) == 1 and ("pedestrian" in  warnings[0] or "Beta-Stadium" in warnings[0]):
			pass
		else:
			cprint ("\n"+_("Warnings")+":", 'red')
			for warning in warnings:
				cprint ("- " + sanitize(warning, cwidth), 'red')


main()
