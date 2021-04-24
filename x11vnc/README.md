# x11vnc server

auto start x11vnc server on boot for Wind River Linux xfce

## install

```bash
    #x11vnc -storepasswd /etc/x11vnc.passwd
    #chown root.root /etc/x11vnc.passwd
    #chmod 644 /etc/x11vnc.passwd
    #./install.sh
```

## customize

edit file /lib/systemd/system/x11vnc.service  

Any changes in the script will be will be applied after the next reboot.  
In order to apply changes immediately, you can run (as root)

```bash
    #systemctl daemon-reload
    #systemctl restart x11vnc.service
```

## status

```bash
    #systemctl status x11vnc.service
```

## uninstall

```bash
    #./uninstall.sh
```
