#!/bin/sh

SHARE_DIR=/share/kocom

if [ ! -f $SHARE_DIR/main.py ]; then
	mkdir $SHARE_DIR
	mv /main.py $SHARE_DIR
fi
/makeconf.sh

echo "[Info] Run Wallpad Controller"
cd $SHARE_DIR
python3 $SHARE_DIR/main.py

# for dev
while true; do echo "still live"; sleep 100; done
