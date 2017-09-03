import json, shelve

shelf = shelve.open('routeset.shelve')
jsonDict = {}
for key, val in shelf.iteritems():
	jsonDict[key] = val
with open("routeset.json","w") as outfile:
	json.dump(jsonDict, outfile, sort_keys=True, indent=4, ensure_ascii=False)
