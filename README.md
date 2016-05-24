## Description

A Telegram bot that sends users configurable updates on next bus timings in Singapore using the [data provided by LTA](http://www.mytransport.sg/content/mytransport/home/dataMall.html), e.g. you can set it to send you a message about 1 minute before your bus arrives so you don't have to keep looking out for it.

## Link

Try it out on Telegram: [@SporeBusBot](http://telegram.me/SporeBusBot)

## Instructions

Put in your Telegram token, app URL, [LTA API credentials](http://www.mytransport.sg/content/mytransport/home/dataMall.html) and Redis details ([OpenShift has a partner provider](https://blog.openshift.com/how-to-use-redis-on-openshift-from-your-ruby-application/)) in flaskapp.cfg, then host it on OpenShift.
