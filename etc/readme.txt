Copy the following files to beaglebone black:

[root]/etc/ppp/ppp_on_boot
[root]/etc/ppp/peers/att
[root]/etc/ppp/peers/att-connect-chat
[root]/etc/ppp/peers/att-disconnect-chat
[root]/etc/ppp/peers/verizon
[root]/etc/ppp/peers/verizon-connect-chat
[root]/etc/ppp/ip-up.d/addroute

Optionally edit options file to include logging
/etc/ppp/options
lock
logfile /var/log/ppp/log #requires debug flag in dialup script

# watch log output by tail -f /var/log/ppp/log
# remove debug flag for production

