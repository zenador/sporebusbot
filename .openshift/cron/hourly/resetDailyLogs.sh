#!/bin/bash

hour=$(date '+%k')
if [ $hour != 14 ]; then #run only at 3 am SGT
    exit
fi

if [ ! -f $OPENSHIFT_DATA_DIR/last_run ]; then
	touch $OPENSHIFT_DATA_DIR/last_run
fi

python $OPENSHIFT_REPO_DIR/resetDailyLogs.py
