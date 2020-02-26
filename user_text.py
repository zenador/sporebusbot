#!/usr/bin/env python

helpText = 'Please enter /help to read about the available commands'

helpTextFull = '''
*QUICKSTART*

Start with any of the following:
- Send your location to see the 5 nearest bus stops
- Enter /starred to see your saved bus stops
- Enter */info [Bus Stop #]* to see information for that bus stop
From there, you can tap the buttons to get next bus alerts.
Or, see below for how to type out full commands.

*DETAILED COMMANDS*

/next - Shows the ETAs for the next few buses
*/next [Bus Stop #] [Bus Route #]*
_/next 17179 184_

/remind - Shows the ETAs for the next few buses and sends another alert X minutes before the next bus according to the first ETA
*/remind [Bus Stop #] [Bus Route #] [X Integer]*
_/remind 17179 184 2_

/track - Shows the ETAs for the next few buses and sends more alerts at decreasing intervals until the next bus is X minutes from arriving
*/track [Bus Stop #] [Bus Route #] [X Integer]*
_/track 17179 184 2_

As an alternative, replace 'track' with 'tracks' to not receive the alerts in the middle, and only get an alert about X minutes before the bus arrives. This works similar to remind, but may be more accurate as it keeps checking in between (sends more queries), though less reliable as it is less tested.

/nag - Shows the ETAs for the next few buses and sends more alerts at X minute intervals for a maximum of Y times
*/nag [Bus Stop #] [Bus Route #] [X Integer] [Y Integer]*
_/nag 17179 184 2 1_

/info - Shows the first and last bus timings for that route at that bus stop, or info about the stop if route is omitted
*/info [Bus Stop #] [Bus Route #]*
_/info 17179 184_
*/info [Bus Stop #]*
_/info 17179_

For all commands, you may omit the bus stop number and route number to use your last successfully queried numbers instead, e.g.
/next

*/remind [X Integer]*
_/remind 2_

*/track [X Integer]*
_/track 2_

*/nag [X Integer] [Y Integer]*
_/nag 2 1_

You may also omit the extra parameters to use your last used settings for that particular command, e.g.
*/remind [Bus Stop #] [Bus Route #]*
_/remind 17179 184_

*/track [Bus Stop #] [Bus Route #]*
_/track 17179 184_

Or you could omit both.
/remind
/track
/nag
/info

/history - Shows your recent commands

/fav - Shows a list of shortcuts to the favourite commands that you have saved

/save - Saves a new command to your favourites
*/save|[command]
[Description of command]*
_/save|remind 17179 184 2
Clementi bus stop_

/delete - Removes an existing command from your favourites
*/delete|[command]
[Description of command]*
_/delete|remind 17179 184 2
Clementi bus stop_

Commands can be entered with or without the starting slash.

Legend for bus timings:
*Seats Available*
Standing Available
_Limited Standing_
(Second Visit)
'''
