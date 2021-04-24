#!/bin/bash

#Require sudo
if [ $EUID != 0 ]; then
    sudo "$0" "$@"
    exit $?
fi

echo "adding service file to /lib/systemd/system/..."
cp x11vnc.service /lib/systemd/system/
chmod 644 /lib/systemd/system/x11vnc.service
echo "done"

echo "starting and enabling x11vnc service..."
systemctl daemon-reload
systemctl start x11vnc.service
systemctl enable x11vnc.service
echo "done"

echo "x11vnc service installed sucessfully!"
echo ""
echo "Please run x11vnc -storepasswd (as root)"
