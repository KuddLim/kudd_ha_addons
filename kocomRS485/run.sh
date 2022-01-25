#!/bin/sh

SHARE_DIR=/share/kocom

if [ ! -f $SHARE_DIR/main.py ]; then
	mkdir $SHARE_DIR
fi

cp /*.py $SHARE_DIR

/makeconf.sh

echo "[Info] listing python files"

for f in *.py; do echo "Python file $f copied"; done

echo "[Info] Run Wallpad Controller"
cd $SHARE_DIR
python3 $SHARE_DIR/main.py
# for dev
while true; do echo "still live"; sleep 100; done
