#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from urllib.request import urlopen
import os.path as op
import pickle
import re
import pandas as pd
import json
import time
import random
import numpy as np
import argparse

def geocode(location): 
	url = 'https://maps.googleapis.com/maps/api/geocode/json'
	params = {'sensor': 'false', 'address': location}
	r = requests.get(url, params=params)
	results = r.json()['results']
	location = results[0]['geometry']['location']
	return({'latitude': location['lat'], 'longitude':location['lng']})

def runscrape(city='Eugene, OR',start_page = None, end_page=None, outfile=None, verbose=False):

	if not start_page:
		start_page=1

	if not end_page:
		end_page = start_page+10

	if not outfile:
		cityname = re.sub(r'\W+',' ',city)
		cityname = re.sub(' ','_',cityname).lower()
		outfile = cityname+'.csv'

	basename, ext = op.splitext(outfile)

	outpkl = basename+'_routedata.pklz'
	routelist = basename+'_routelist.pklz'



	coords = geocode(city)
	
	print('Getting Routes for %s (%s)' %(city,str(coords)))

	myquery = urlencode({'location': city, 'lat': coords['latitude'],
								'lon': coords['longitude'], 'activityType': 'RUN','distance':''})

	if op.exists(routelist):
		with open(routelist,'rb') as f:
			allllinks = pickle.load(f)
	else:
		alllinks = []

	for page in range(start_page,end_page+1):
		
		print("page %d" % page)
		url='https://runkeeper.com/search/routes/%d?%s' %(page,myquery)
		
		if verbose:
			print(url)

		r = urlopen(url).read()
		soup = BeautifulSoup(r,'html.parser')

		divs = soup.find_all("a",{'class' :'thumbnailUrl'})
		links = [x.get('href') for x in divs]
		
		if len(links)==0:
			break
		else:
			alllinks.extend(links)
			
			if(len(alllinks)%12==0):

				with open(routelist,'wb') as f:
					pickle.dump(alllinks,f)
			if verbose:
				print("First link: %s" % links[0])

			time.sleep(random.choice([1.1,2.2,1.7]))



	# #save the route URLs
	# with open('routes.json', 'w') as outfile:
	#     json.dump(alllinks, outfile)
	   

	#   #load up the route URLs
	# with open('/Users/thrillhouse/Dropbox/teaching/psy407_programming/scripts/datasets/runkeeper/corvallis_links.json') as f:    
	#     alllinks = json.load(f)


	allpaths = []

	print('Scraping route data from %d routes...' % len(alllinks))
	for routenum,l in enumerate(alllinks): 
		
		if verbose:
			print("getting route from %s" %l)
		user = l.strip().split('/')[2]

		
		routeURL = "https://runkeeper.com%s" %l
		
		try:
			response = urlopen(routeURL)
		
		except URLError as e:
			if hasattr(e, 'reason'):
				print('We failed to reach a server.')
				print('Reason: ', e.reason)
			elif hasattr(e, 'code'):
				print('The server couldn\'t fulfill the request.')
				print('Error code: ', e.code)
		else:
		
			routeR = response.read()
			route = BeautifulSoup(routeR,'html.parser')
			points = route.find_all('script')
			
			finder = re.compile('routePoints\s+=.*;')
			findpoints = [finder.findall(p.text) for p in points]
			findpoints = [x for x in findpoints if len(x)>0]
			
			if len(findpoints)>0:
				pointdata = findpoints[0][0]
				pointdata = pointdata.split('=')[1]
				pointdata = pointdata.replace(';','')
				pathjson = json.loads(pointdata)

				pathDF = pd.DataFrame.from_dict(pathjson)
				
				pathDF['user'] = np.repeat(user,len(pathDF.latitude))
				pathDF['routenum'] = np.repeat(routenum,len(pathDF.latitude))
				
				allpaths.append(pathDF)
			
			with open(outpkl,'wb') as f:
				pickle.dump(allpaths,f)

			time.sleep(random.choice([.75,1.1,.85]))
		

	allrundata = pd.concat(allpaths,axis=0)

	allrundata.routenum = allrundata.routenum+1

	print('Saving data to %s' % outfile)
	
	if op.exists(outfile):
		with open(outfile, 'a') as f:
			allrundata.to_csv(f, header=False)
	else:
		allrundata.to_csv(outfile, header=True)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("city", help='City to download data from (example: "Eugene, OR"')
	parser.add_argument("--start_page", type=int,help='Starting page on Runkeeper site (can use this to resume from previous download)')
	parser.add_argument("--end_page",  type=int,  help='End page on Runkeeper site')
	parser.add_argument("--outfile", help='Path to csv file to save data')
	parser.add_argument('--verbose', action='store_true', help='Verbose mode. Print as we download data')
	args = parser.parse_args()

	runscrape(city=args.city, outfile=args.outfile, start_page=args.start_page,end_page=args.end_page, verbose = args.verbose)

