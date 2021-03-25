#!/bin/sh

#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

# put other system startup commands here

#
# Change the 'tc' password
#
echo 'tc:tc' | chpasswd

#
# Get the variables
#
. /opt/km_variables

#
# In case we are booting the base image, set the default variables
#
if [ "${HOSTNAME}" = "base" ]; then
	SCENARIO=NxM
	HOSTNAME=nsim_base
	NETMASK=255.255.0.0
	GATEWAY=172.16.1.1
	NAMESERVER=208.67.222.222
	LOGGER=172.16.1.92
fi

#
# Set the hostname
#
/usr/bin/sethostname ${HOSTNAME}

#
# Copy the correct hosts file.
#
cp -fp /opt/hosts.${SCENARIO} /etc/hosts
chmod 644 /etc/hosts

#
# Bring up the ethernet interface.
#
ifconfig eth0 ${HOSTNAME} netmask ${NETMASK} up
route add default gw ${GATEWAY}
echo "nameserver ${NAMESERVER}" > /etc/resolv.conf

#
# Start ACPID
#
mkdir /usr/local/etc/acpi/actions

cp /opt/acpi.events /usr/local/etc/acpi/events/power
cp /opt/acpi.actions /usr/local/etc/acpi/actions/power-button.sh
acpid -c /usr/local/etc/acpi

#
# Start SSHD
#
cp /opt/sshd_config.orig /usr/local/etc/ssh/sshd_config
/usr/local/etc/init.d/openssh start
