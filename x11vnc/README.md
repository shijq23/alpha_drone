# x11vnc server

auto start x11vnc server on boot for Wind River Linux xfce

## install

run (as root)
    #x11vnc -storepasswd
    #./install.sh

## customize

edit file /lib/systemd/system/x11vnc.service  

Any changes in the script will be will be applied after the next reboot.  
In order to apply changes immediately, you can run (as root)
    #systemctl daemon-reload
    #systemctl restart x11vnc.service

## status

run (as root)
    #systemctl status x11vnc.service

## uninstall

run (as root)
    #./uninstall.sh
