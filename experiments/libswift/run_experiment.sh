#!/bin/bash -xe
# %*% Executes libswift experiment. Note that build_experiment.sh should be run before this.
# %*% Starts 1 seeder in a container and connects $NO_OF_LEECHERS leechers to it to download a file.

# Set defaults for config variables ---------------------------------------------------
# Override these on Jenkins before running the script.

# @CONF_OPTION EXPERIMENT_TIME: Process guard timeout in seconds, set to 0 to disable (default: 30)
[ -z "$EXPERIMENT_TIME" ] && EXPERIMENT_TIME=30
# @CONF_OPTION NO_OF_LEECHERS: Number of leechers to start (default 1)
[ -z "$NO_OF_LEECHERS" ] && NO_OF_LEECHERS="1"
# ------------------------------------------------------------------------------

# clean up in case of an early exit
function cleanup {
  echo "Cleaning up"
	sudo /usr/bin/lxc-stop -n seeder
	wait
	# umount the union filesystem
	if mount | grep $CONTAINER_DIR; then
		sudo /bin/umount $CONTAINER_DIR -l
	fi
	if mount | grep /tmp/container; then
		sudo /bin/umount /tmp/container	-l
	fi
	rmdir $CONTAINER_DIR
}
trap cleanup EXIT
trap cleanup TERM

# check if netem config is set correctly
# heterogeneous delay?
# @CONF_OPTION NETEM_DELAY: Netem delay for the leechers. Note: for a homogeneous network of leechers, set 1 value
# @CONF_OPTION NETEM_DELAY: for a heterogeneous network separate values by , e.g. netem_delay = "0ms,100ms"
# @CONF_OPTION NETEM_DELAY: for variation in delay, separate config option with _, e.g. netem_delay = "0ms_10ms,100ms"
if [[ $NETEM_DELAY == *,* ]]
then
	# split in array
	DELAY=(`echo $NETEM_DELAY | tr ',' ' '`)
	if [[ ${#DELAY[@]} != $NO_OF_LEECHERS ]]
	then
		echo "No of delay settings should be equal to 1 or the number of leechers"
		exit 65
	fi
	HETEROGENEOUS_DELAY=true
else
	DELAY=$NETEM_DELAY
	HETEROGENEOUS_DELAY=false
fi

# @CONF_OPTION NETEM_PACKET_LOSS: Packet loss in % (can also be hetero/homogeneous) for leechers.
# @CONF_OPTION NETEM_PACKET_LOSS: set 1 value, for a heterogeneous network separate values by ,
# @CONF_OPTION NETEM_PACKET_LOSS: e.g. leecher_offset="0%,5%" (note that the number of elements should then match the number of leechers)
if [[ $NETEM_PACKET_LOSS == *,* ]]
then
	# split in array
	PACKET_LOSS=(`echo $NETEM_PACKET_LOSS | tr ',' ' '`)
	if [[ ${#PACKET_LOSS[@]} != $NO_OF_LEECHERS ]]
	then
		echo "No of packet loss settings should be equal to 1 or the number of leechers"
		exit 65
	fi
	HETEROGENEOUS_PACKET_LOSS=true
else
	PACKET_LOSS=$NETEM_PACKET_LOSS
	HETEROGENEOUS_PACKET_LOSS=false
fi

# @CONF_OPTION NETEM_RATE: # Rate download limit for leechers (e.g., 100mbit). Note: for a homogeneous network of leechers,
# @CONF_OPTION NETEM_RATE: set 1 value, for a heterogeneous network separate values by ,
# @CONF_OPTION NETEM_RATE: e.g. leecher_offset="1mbit,100mbit" (note that the number of elements should then match the number of leechers)
if [[ $NETEM_RATE == *,* ]]
then
	# split in array
	RATE=(`echo $NETEM_RATE | tr ',' ' '`)
	if [[ ${#RATE[@]} != $NO_OF_LEECHERS ]]
	then
		echo "No of rate limit settings should be equal to 1 or the number of leechers"
		exit 65
	fi
	HETEROGENEOUS_RATE=true
else
	RATE=$NETEM_RATE
	HETEROGENEOUS_RATE=false
fi

# @CONF_OPTION NETEM_RATE_UL: # Rate upload limit for leechers (e.g., 100mbit). Note: for a homogeneous network of leechers,
# @CONF_OPTION NETEM_RATE_UL: set 1 value, for a heterogeneous network separate values by ,
# @CONF_OPTION NETEM_RATE_UL: e.g. leecher_offset="1mbit,100mbit" (note that the number of elements should then match the number of leechers)
if [[ $NETEM_RATE_UL == *,* ]]
then
	# split in array
	RATE_UL=(`echo $NETEM_RATE_UL | tr ',' ' '`)
	if [[ ${#RATE_UL[@]} != $NO_OF_LEECHERS ]]
	then
		echo "No of upload rate limit settings should be equal to 1 or the number of leechers"
		exit 65
	fi
	HETEROGENEOUS_RATE_UL=true
else
	RATE_UL=$NETEM_RATE_UL
	HETEROGENEOUS_RATE_UL=false
fi

# @CONF_OPTION LEECHER_OFFSET: Time in seconds between startup of leechers. Note: for a homogeneous network of leechers,
# @CONF_OPTION LEECHER_OFFSET: set 1 value, for a heterogeneous network separate values by ,
# @CONF_OPTION LEECHER_OFFSET: e.g. leecher_offset="0,100" (note that the number of elements should then match the number of leechers)
if [[ $LEECHER_OFFSET == *,* ]]
then
	# split in array
	OFFSET=(`echo $LEECHER_OFFSET | tr ',' ' '`)
	if [[ ${#OFFSET[@]} != $NO_OF_LEECHERS ]]
	then
		echo "No of offset settings should be equal to 1 or the number of leechers"
		exit 65
	fi
	HETEROGENEOUS_OFFSET=true
else
	OFFSET=$LEECHER_OFFSET
	HETEROGENEOUS_OFFSET=false
fi

# @CONF_OPTION LEECHER_TIME: Time a leecher will remain running (optional),
# @CONF_OPTION LEECHER_TIME: set 1 value, for a heterogeneous network separate values by ,
# @CONF_OPTION LEECHER_TIME: e.g. leecher_time="100s,200s" (note that the number of elements should then match the number of leechers)
if [ ! -z "$LEECHER_TIME" ]; then
	if [[ $LEECHER_TIME == *,* ]]
	then
	# split in array
		TIME=(`echo $LEECHER_TIME | tr ',' ' '`)
		if [[ ${#TIME[@]} != $NO_OF_LEECHERS ]]
		then
			echo "No of offset settings should be equal to 1 or the number of leechers"
			exit 65
		fi
		HETEROGENEOUS_TIME=true
	else
		TIME=$LEECHER_TIME
		HETEROGENEOUS_TIME=false
	fi
else
	TIME=0
	HETEROGENEOUS_TIME=false
fi

# @CONF_OPTION DEBUG_SWIFT: Store libswift debug output (optional).
if [ -z "$DEBUG_SWIFT" ]; then
	DEBUG_SWIFT=false
fi

# get full path, easier for use in container
WORKSPACE_DIR=$(readlink -f $WORKSPACE_DIR)
FILENAME=file_seed.tmp


echo "Running swift processes for $EXPERIMENT_TIME seconds"
echo "Workspace: $WORKSPACE_DIR"
echo "Output dir: $OUTPUT_DIR"

if $IPERF_TEST;
then
	HASH=3
else
	# wait for the hash to be generated - note that this happens in the container fs
	while [ ! -f $OUTPUT_DIR/$FILENAME.mbinmap ] ;
	do
	      sleep 2
	done

	HASH=$(grep hash $OUTPUT_DIR/$FILENAME.mbinmap | cut -d " " -f 3)
fi

for (( i = 0 ; i < $NO_OF_LEECHERS; i++ ))
do
	# read delay and packet loss
	if $HETEROGENEOUS_DELAY;
	then
		LEECHER_DELAY=${DELAY[$i]}
	else
		LEECHER_DELAY=$DELAY
	fi

	if $HETEROGENEOUS_PACKET_LOSS;
	then
		LEECHER_PACKET_LOSS=${PACKET_LOSS[$i]}
	else
		LEECHER_PACKET_LOSS=$PACKET_LOSS
	fi

	if $HETEROGENEOUS_RATE;
	then
		LEECHER_RATE=${RATE[$i]}
	else
		LEECHER_RATE=$RATE
	fi

	if $HETEROGENEOUS_RATE_UL;
	then
		LEECHER_UL_RATE=${RATE_UL[$i]}
	else
		LEECHER_UL_RATE=$RATE_UL
	fi

	if $HETEROGENEOUS_OFFSET;
	then
		sleep ${OFFSET[$i]}
	else
		sleep $OFFSET
	fi

	if $HETEROGENEOUS_TIME;
	then
		LEECHER_TIME=${TIME[$i]}
	else
		LEECHER_TIME=$TIME
	fi

	# @CONF_OPTION NETWORK_IP_RANGE: First part of IP of local network to use for leecher IPs (e.g., 192.168.1)
	# @CONF_OPTION LEECHER_ID: Last part of IP of first leecher. Will be incremented for additional leechers (e.g., 111)

	LEECHER_IP=$NETWORK_IP_RANGE.$(($LEECHER_ID+$i))
	sudo /usr/bin/lxc-execute -n leecher_$i \
		-s lxc.network.type=veth \
		-s lxc.network.flags=up \
		-s lxc.network.link=$BRIDGE_NAME \
		-s lxc.network.ipv4=$LEECHER_IP/24 \
		-s lxc.rootfs=$CONTAINER_DIR \
		-s lxc.pts=1024 \
		-- $WORKSPACE_DIR/$LEECHER_CMD $WORKSPACE_DIR/swift $OUTPUT_DIR $HASH $LEECHER_DELAY $LEECHER_PACKET_LOSS $WORKSPACE_DIR/gumby/scripts/process_guard.py $EXPERIMENT_TIME $BRIDGE_IP $SEEDER_IP $SEEDER_PORT $OUTPUT_DIR $(($LEECHER_ID+$i)) $USER $LEECHER_RATE $LEECHER_UL_RATE $IPERF_TEST $TIME $DEBUG_SWIFT &
done


wait

# remove leeched files
for (( i = 0 ; i < $NO_OF_LEECHERS; i++ ))
do
	LEECHER_ID_TMP=$(($LEECHER_ID+$i))
	rm -f $OUTPUT_DIR/dst/$LEECHER_ID_TMP/$HASH*
done





