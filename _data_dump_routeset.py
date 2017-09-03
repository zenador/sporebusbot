import json
import shelve

import requests

if __name__=="__main__":

	jsonDict = {}

	LTA_ACCOUNT_KEY = 'YOUR LTA ACCOUNT KEY'

	#Authentication parameters
	headers = {
		'AccountKey' : LTA_ACCOUNT_KEY,
		'accept' : 'application/json', #Request results in JSON
	}

	#API parameters
	target = 'http://datamall2.mytransport.sg/ltaodataservice/BusRoutes' #Resource URL

	skippy = 0
	results = 50

	while (results > 0):
		#Query parameters
		params = {"$skip": skippy}

		#Obtain results
		r = requests.get(target, params=params, headers=headers)

		#Parse JSON to print
		jsonObj = json.loads(r.content)
		#print json.dumps(jsonObj, sort_keys=True, indent=4)

		dictList = jsonObj["value"]
		for dicty in dictList:
			key = "{}_{}_{}".format(dicty['BusStopCode'], dicty['ServiceNo'], dicty['Direction'])
			jsonDict[key] = dicty

		skippy += 50
		results = len(dictList)
		print results, skippy

	#Save result to file
	# with open("routeset_updated.json","w") as outfile:
	# 	json.dump(jsonDict, outfile, sort_keys=True, indent=4, ensure_ascii=False)

	shelf = shelve.open('routeset.shelve')
	#shelf.update(jsonDict) #not working with unicode keys
	for key in jsonDict:
		shelf[str(key)] = jsonDict[key]
	shelf.close()
