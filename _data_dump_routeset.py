import json 
import urllib 
from urlparse import urlparse 
import shelve
 
import httplib2 as http #External library 
 
if __name__=="__main__": 
	 
	jsonDict = {}

	LTA_ACCOUNT_KEY = 'YOUR LTA ACCOUNT KEY'
	LTA_USER_ID = 'YOUR LTA USER ID'
 
	#Authentication parameters 
	headers = { 'AccountKey' : LTA_ACCOUNT_KEY,  
				'UniqueUserID' : LTA_USER_ID, 
				'accept' : 'application/json'} #Request results in JSON 

	#API parameters 
	uri = 'http://datamall.mytransport.sg' #Resource URL 
	#path = '/ltaodataservice.svc/SMRTRouteSet?'
	#path = '/ltaodataservice.svc/SBSTRouteSet?'
	pathSet = ['/ltaodataservice.svc/SBSTRouteSet?', '/ltaodataservice.svc/SMRTRouteSet?']

	for path in pathSet:

		skippy = 0
		results = 50

		while (results > 0):
			#Query parameters
			params = {'$skip': str(skippy)}
		 
			#Build query string & specify type of API call 
			target = urlparse(uri + path + urllib.urlencode( params ) )
			print target.geturl() 
			method = 'GET' 
			body = '' 
			 
			#Get handle to http 
			h = http.Http() 
		 
			#Obtain results 
			response, content = h.request(target.geturl(), method, body, headers) 
		 
			#Parse JSON to print 
			jsonObj = json.loads(content)
			#print json.dumps(jsonObj, sort_keys=True, indent=4) 

			for dicty in jsonObj["d"]:
				key = dicty['SR_BS_CODE']+'_'+dicty['SR_SVC_NUM']+'_'+dicty['SR_SVC_DIR']
				jsonDict[key] = dicty

			skippy += 50
			results = len(jsonObj["d"])
			print results

	#Save result to file
	# with open("routeset_updated.json","w") as outfile:
	# 	json.dump(jsonDict, outfile, sort_keys=True, indent=4, ensure_ascii=False)

	shelf = shelve.open('routeset.shelve')
	#shelf.update(jsonDict) #not working with unicode keys
	for key in jsonDict:
		shelf[str(key)] = jsonDict[key]
	shelf.close()
