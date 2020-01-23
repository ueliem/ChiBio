#!/bin/bash

installdir="/root/chibio/"
repodir=$(dirname "$(readlink -f "$0")")

if [[ $(id -u) -ne 0 ]]; then
	echo "This script must be run as root"
	exit 1
fi

cd /etc/ssh/
echo "PermitRootLogin yes" >> sshd_config
echo -e "root\nroot" | passwd root
sed -i 's@-w /var/lib/cloud9@-w /root/chibio@' /lib/systemd/system/cloud9.service
sed -i 's@1000@root@' /lib/systemd/system/cloud9.service
cd /etc/
echo -e "nameserver 8.8.8.8\nnameserver 8.8.4.4" >> resolv.conf
/sbin/route add default gw 192.168.7.1
systemctl restart systemd-timesyncd
apt update
apt --assume-yes upgrade
mkdir -p $installdir
cd $repodir
cp cb.sh $installdir
cp app.py $installdir
cp static -r $installdir
cp templates -r $installdir
cp chibio.service /etc/systemd/system/chibio.service
apt --assume-yes install python-pip
pip install Gunicorn
pip install flask
pip install serial
pip install Adafruit_GPIO
pip install --user --upgrade setuptools
pip install simplejson
pip install smbus2
pip install numpy
cd /tmp/
pip download Adafruit_BBIO
tar xvzf Adafruit_BBIO-1.1.1.tar.gz
cd Adafruit_BBIO-1.1.1/
sed -i "s/'-Werror', //g" setup.py
python setup.py install
cd $installdir
chmod +x cb.sh
systemctl daemon-reload
systemctl enable chibio
systemctl start chibio
reboot now
