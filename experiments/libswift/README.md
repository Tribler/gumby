Libswift experiment setup details
=================================

This experiment transfers a file between 1 seeder and 1 leecher using libswift. It is possible to configure a netem
delay for the leecher.

## Setup ##

### Dependencies ###

sudo apt-get install lxc bridge-utils libevent-2-0-5 aufs-tools

### Sudoers file ###
It is useful to add the following commands to the /etc/sudoers file using sudo visudo:

```
USER ALL=NOPASSWD:/usr/bin/lxc-execute,/bin/mount
```

Especially for USER jenkins as this prevents sudo from asking for a password during execution of the experiment. 

### Network bridge ###

(Note: this assumes your network device is eth0)

Add the bridge to /etc/network/interfaces:

```
iface br0 inet static
       bridge_ports none
       bridge_fd 0
       address 192.168.1.20
       netmask 255.255.255.0
       network 192.168.1.0
       broadcast 192.168.1.255
```

```
sudo ifup br0
```

sudo ifconfig should show the br0 with IP 192.168.1.20.
Forward the traffic from/to the containers:

```
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -i br0 -o eth0 -j ACCEPT
```

Set /proc/sys/net/ipv4/ip_forward to 1. If you want to use the network on the containers, enter the following commands inside the container:

```
route add default gw 192.168.1.20
echo nameserver 8.8.8.8 >> /etc/resolv.conf
```

Probably forgot some steps so feel free to add them.

## Quick Start ##

Edit libswift.conf and (from the workspace directory) run:

```
gumby/run.py gumby/experiments/libswift/libswift.conf
```

## Experiment Components ##

### init.sh ###

Used to initialize the container's filesystem. Most of the packages (lxc, python, etc) are installed using the lxc template
lxc-debian-libswift, but some are not available in the repository. Therefore they have to be built manually using this shell script.

### leecher_config & seeder_config ###

Configuration templates for the leecher & seeder containers. Configured using values from libswift.conf.

### libswift.conf ###

The experiment configuration file.

### lxc-debian-libswift ###

Template for creating a debootstrap installation with the dependencies for this experiment.

### parse_logs.py, resource_usage.gnuplot & speed.gnuplot ###

Resource usage graph generation stuff. Currently broken, originally created by @vladum.

### start_leecher.sh & start_seeder.sh ###

Scripts used to start the leecher and seeder (run inside the container).


## Creating a union filesystem for the container ##

```
sudo apt-get install aufs-tools
mkdir /tmp/container
mkdir /tmp/aufs-root
sudo mount -t tmpfs none /tmp/container/
sudo mount -t aufs -o br=/tmp/container:/ none /tmp/aufs-root
```

(use /tmp/aufs-root as rootfs for the containers)