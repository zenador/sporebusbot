## Description

A Telegram bot that sends users configurable updates on next bus timings in Singapore using the [data provided by LTA](http://www.mytransport.sg/content/mytransport/home/dataMall.html), e.g. you can set it to send you a message about 1 minute before your bus arrives so you don't have to keep looking out for it.

## Link

Try it out on Telegram: [@SporeBusBot](http://telegram.me/SporeBusBot)

## Instructions

1. Put in the following details in `flaskapp.cfg` directly or set them as environment variables accordingly (for OpenShift Online, managed under applications/deployments and not builds or image), then host it on OpenShift with Python 3 (redirect https under routing).
    - Telegram bot token
    - [LTA API credentials](http://www.mytransport.sg/content/mytransport/home/dataMall.html)
    - App URL
    - Redis details (from OpenShift, or you can use [Redis Cloud](https://redislabs.com/redis-cloud))
    - [Posthook](https://posthook.io/) API key and signature
2. To run the server, `python runapp.py`. To run serverless, use `flaskapp.py`.
3. When setting up your Telegram bot for the first time, visit the following URL (based on your values in Step 1) in your browser to set up your webhook: APP_URL/TOKEN/set_webhook
