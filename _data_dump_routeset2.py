import json, shelve

with open("routeset.json","r") as thefile:
	jsonDict = json.load(thefile)
	shelf = shelve.open('routeset.shelve')
	#shelf.update(jsonDict) #not working with unicode keys
	for key in jsonDict:
		shelf[str(key)] = jsonDict[key]
	shelf.close()
