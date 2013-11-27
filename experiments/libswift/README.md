Libswift experiment setup details
=================================

This experiment transfers a file between 1 seeder and x leechers using libswift. It is possible to configure a netem
delay and packet loss for the leechers.

## Setup ##

### Dependencies ###

sudo apt-get install lxc bridge-utils libevent-2.0.5 aufs-tools

### LXC ###

Cgroups are a kernel feature that's needed for lxc to run properly. Start by adding the following to your /etc/fstab file:

```
cgroup  /sys/fs/cgroup  cgroup  defaults  0   0
```

Mount it:

```
sudo mount /sys/fs/cgroup
```

### Sudoers file ###
It is useful to add the following commands to the /etc/sudoers file using sudo visudo:

```
%USER% ALL=NOPASSWD:/usr/bin/lxc-execute,/bin/mount,/bin/umount,/usr/bin/lxc-stop
```

Especially for user jenkins as this prevents sudo from asking for a password during execution of the experiment. 
(note: replace %USER% with the username of the user that will run the experiment)

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

### build_experiment.sh (local_setup_cmd) ###

Used to initialize the container's filesystem - note that we use the existing filesystem by mounting it as a union
filesystem -. Does the following:
- Mounts root filesystem and creates temporary filesystem on top
- Creates output directory
- Creates the file to seed 
- Downloads and compiles libswift from $REPOSITORY_DIR 

### libswift.conf ###

The experiment configuration file.

### parse_logs.py, resource_usage.gnuplot & speed.gnuplot ###

Resource usage graph generation stuff. Currently broken, originally created by @vladum.

### run_experiment.sh (local_instance_cmd) ###
Runs the experiment. First waits for the hash of the seeded file to be generated, then starts the leecher(s) to download
this file. After all the leechers are done, the plots are generated if $GENERATE_PLOTS is set to true. Finally, gumby 
closes the seeder.

### start_seeder.sh (tracker_cmd) ###
Starts the seeder before the experiment is started. Also generates the hash of the file to seed.

### start_leecher.sh  ###
Scripts used to start the leecher(s) (run inside the container).


## Creating a union filesystem for the container ##

```
sudo apt-get install aufs-tools
mkdir /tmp/container
mkdir /tmp/aufs-root
sudo mount -t tmpfs none /tmp/container/
sudo mount -t aufs -o br=/tmp/container:/ none /tmp/aufs-root
```

(use /tmp/aufs-root as rootfs for the containers)