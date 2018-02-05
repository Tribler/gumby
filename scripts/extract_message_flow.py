#!/bin/python2
import os
import re
import getopt
import sys


def usage():
    print
    print "CaptainCoder's super-duper gumby messaging flow extraction script."
    print "Extracts a flow chart of all messages sent and received by the experiment runners"
    print
    print "Usage:"
    print "   extract_message_flow.py [--color] [--deduplicate] [--exclude-service <service>[,<service>]...] "
    print "       [--exclude-service <service>[,<service>]...] [--tunnel-collapse] [--reduced] [--message-format "
    print "       <format-string>] [--no-port-events] [--no-message-events] [<file root>]"
    print
    print "Arguments:"
    print "   <file_root>"
    print "       Root directory where experiment runner output files may be found named 00000.out, 00001.out, etc."
    print "       Defaults to './output'"
    print
    print "Options:"
    print "   --color  -c"
    print "       Prints output using ANSI terminal color codes. This makes it easy to follow output lines"
    print "   --deduplicate  -d"
    print "       Suppresses output of receive lines that have a matching outgoing line"
    print "   --exclude-service <service>[,<service>]...  -s <service>[,<service>]..."
    print "       Exclude messages to/from a specific service. Services include dispersy, dht, torrent, socks5"
    print "       Specify a comma separated service list to exclude multiple services"
    print "   --exclude-message <message>[,<message>]...  -m <message>[,<message>]..."
    print "       Exclude message types that are prefixed by the argument. Specify a comma separated service list to "
    print "       filter multiple services"
    print "   --tunnel-collapse  -t"
    print "       Suppresses output of intermediate tunnel hops"
    print "   --message-format <format-string>  -f<format-string>"
    print "       Uses <format-string> to format the string representation of messages"
    print "   --no-port-events  -p"
    print "       Suppresses output of port events"
    print "   --no-message-events  -e"
    print "       Suppresses output of message events"
    print "   --reduced  -r"
    print "       Equivalent to -d -t -p -m dispersy-,similarity-,ping,pong,cell,crawl and a reduced format string"
    print
    sys.exit(1)


file_root = u"output"
color = False
deduplicate = False
collapse = False
exclude_service = []
exclude_message = []
output_messages = True
output_ports = True
message_format = "{0.time} {0.host_service[0]:>10} {0.host:<2} {0.direction} {0.type:^38} {0.direction} {0.peer:>2} " \
                 "{0.peer_service[0]:<10} {0.size:>4} {0.circuit:>11} {0.previous_circuit:>11} {0.dest:>4} " \
                 "{0.dest_service:<25}"

try:
    opts, args = getopt.getopt(
        sys.argv[1:],
        "cdrspef:m:t:",
        ["color", "deduplicate", "tunnel-collapse", "exclude-service=", "exclude-message=", "message-format=",
         "reduced", "no-port-events", "no-message-events"])
except BaseException, e:
    print e
    usage()

if len(args) > 1:
    usage()
elif len(args) == 1:
    file_root = unicode(args[0])

for opt, arg in opts:
    if opt in ["-c", "--color"]:
        color = True
    elif opt in ["-d", "--deduplicate"]:
        deduplicate = True
    elif opt in ["-t", "--tunnel-collapse"]:
        collapse = True
    elif opt in ["-s", "--exclude-service"]:
        for service in arg.split(','):
            exclude_service.append(service)
    elif opt in ["-m", "--exclude-message"]:
        for message in arg.split(','):
            exclude_message.append(message)
    elif opt in ["-f", "--message-format"]:
        message_format = arg
    elif opt in ["-p", "--no-port-events"]:
        output_ports = False
    elif opt in ["-e", "--no-message-events"]:
        output_messages = False
    elif opt in ["-r", "--reduced"]:
        collapse = True
        deduplicate = True
        output_ports = False
        exclude_message = exclude_message + ["dispersy-", "similarity-", "ping", "pong", "cell", "crawl"]
        message_format = '{0.time} {0.host_service[1]:>15} {0.host:<3} {0.direction} {0.type:^18} {0.direction} ' \
                         '{0.peer:>3} {0.peer_service[1]:<15} {0.size:>4}'

exclude_message = tuple(exclude_message)
exclude_service = tuple(exclude_service)

OUT = "->"
IN = "<-"
TUNNEL_OVERHEAD = 70
identity_map = {}
service_map = {}
next_out_metadata = {}
ordered_events = []
timestamp_re = re.compile("\s+\d{10}\.\d{0,4}\s+")
dispersy_event_re = re.compile("([a-zA-Z0-9?_-]+)\s+(<-|->)\s+(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}):(\d+)\s+(\d+)\s+bytes"
                               "(?:\s+local\s+\('(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})',\s+(\d+)\))?(?:\s+circuit_id\s+"
                               "(\d+))?")
routing_event_out_re = re.compile("Tunnel data \(len (\d+)\) to end for circuit (\d+) with ultimate destination \('("
                                  "\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})', (\d+)\)")
routing_event_in_re = re.compile("Tunnel data to origin \('(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})', (\d+)\) for circuit "
                                 "(\d+)")
relay_event_re = re.compile("Relay data from (\d+) to (\d+)")
port_res = [
    (re.compile("Get random port (\d+) for \[(.+)\]"), None),
    (re.compile("Dispersy core ready .* port:(\d+)"), ("dispersy", "client")),
    (re.compile("uPnP port added : (\d+) udp"), None),
    (re.compile("Started libtorrent session for.*listen_interfaces': '0.0.0.0:(\d+)"), ("torrent", "libtorrent")),
    (re.compile("SocksUDPConnection starting on (\d+)"), ("socks5", "socks-private")),
    (re.compile("Factory starting on (\d+)"), ("socks5", "socks-server")),
    (re.compile("TunnelExitSocket starting on (\d+)"), ("socks5", "socks-public")),
    (re.compile("SOCKS5 TCP connection made \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:(\d+)"), ("socks5", "socks-client"))
]


class Event(object):
    def __init__(self, time, host):
        assert time is not None and isinstance(time, (float, int, long)), "time must be numerical"
        assert host is not None and isinstance(host, int), "Host must exist and be a number"

        self.time = time
        if str(host) in identity_map:
            self.host = identity_map[str(host)]
        else:
            self.host = host

    def is_suppressed(self):
        return False


class PortEvent(Event):
    def __init__(self, time, host, port, host_service=None):
        assert port is not None and isinstance(port, int), "Port must be a number"

        super(PortEvent, self).__init__(time, host)
        self.host_port = port

        if host_service is None:
            self.host_service = get_service(port)
        else:
            self.host_service = host_service

    def __str__(self):
        return "PORT: %s opened %s service %s" % (self.host, self.host_port, self.host_service)

    def is_suppressed(self):
        return not output_ports


class MessageEvent(Event):
    def __init__(self, time, host, peer, direction, message_type, size = None, circuit = None, prev_circuit = None,
                 dest = None, host_service = None, peer_service = None, dest_service = None):
        assert peer is not None, "Secondary must not be None"
        assert direction == IN or direction == OUT, "Impossible direction"
        assert message_type is not None, "Type must not be None"

        super(MessageEvent, self).__init__(time, host)

        self.time = time
        self.host_service = host_service
        if str(host) in identity_map:
            if self.host_service is None:
                self.host_service = get_service(host)
            host = identity_map[str(host)]
        self.host = host
        self.peer_service = peer_service
        if peer in identity_map:
            if self.peer_service is None:
                self.peer_service = get_service(int(peer))
            peer = identity_map[peer]
        self.peer = peer
        self.direction = direction
        self.type = message_type

        if host in next_out_metadata and direction == OUT:
            metadata = next_out_metadata[host]
            if size is not None and metadata[0] != int(size):
                if metadata[0] is not None:
                    print "ERROR: message size mismatch. Possible wrong ordering?"
                metadata[0] = int(size)
            if circuit is not None and metadata[1] != int(circuit):
                if metadata[1] is not None:
                    print "ERROR: message circuit id mismatch. Possible wrong ordering?"
                metadata[1] = int(circuit)
            if prev_circuit is not None and metadata[2] != int(prev_circuit):
                if metadata[2] is not None:
                    print "ERROR: message circuit id mismatch. Possible wrong ordering?"
                metadata[2] = int(prev_circuit)
            if dest is not None and str(metadata[3]) != str(dest):
                if metadata[3] is not None:
                    print "ERROR: message dest mismatch. Possible wrong ordering?"
                metadata[3] = str(dest)
            del next_out_metadata[host]
        else:
            metadata = [int(size) if size is not None else None, int(circuit) if circuit is not None else None,
                        int(prev_circuit) if prev_circuit is not None else None, dest]

        self.size = metadata[0]
        self.circuit = metadata[1]
        self.previous_circuit = metadata[2]
        dest = metadata[3]
        self.dest_service = dest_service
        if dest is not None and dest in identity_map:
            if self.dest_service is None:
                self.dest_service = get_service(int(dest))
            dest = identity_map[dest]
        self.dest = dest
        self.previous = None
        self.next = None

    def __str__(self):
        old_host_service, old_peer_service = self.host_service, self.peer_service
        if not self.host_service:
            self.host_service = (None, None)
        if not self.peer_service:
            self.peer_service = (None, None)
        return_string = message_format.format(self)
        self.host_service, self.peer_service = old_host_service, old_peer_service
        return return_string

    def set_previous(self, previous):
        if previous.next is not None:
            print "ERROR: proposed previous already has a next"
            return
        if self.previous is not None:
            print "ERROR: event already has a previous"
            return
        previous.next = self
        self.previous = previous

    def set_next(self, item):
        if item.previous is not None:
            print "ERROR: proposed next already has a previous"
            return
        if self.next is not None:
            print "ERROR: event already has a next"
            return
        item.previous = self
        self.next = item

    def combine(self, item):
        self.circuit = item.circuit if self.circuit is None and self.direction == IN else self.circuit
        self.previous_circuit = item.previous_circuit if self.circuit == item.circuit else self.previous_circuit
        self.dest = item.dest if self.circuit == item.circuit else self.dest
        self.dest_service = item.dest_service if self.circuit == item.circuit else self.dest_service

    def matches(self, other):
        return (self.direction == OUT and other.direction == IN or self.direction == IN and other.direction == OUT) and\
            self.host == other.peer and self.peer == other.host and \
            self.host_service == other.peer_service and self.peer_service == other.host_service and \
            self.type == other.type and self.size == other.size and \
            (self.circuit is None or other.circuit is None or self.circuit == other.circuit)

    def is_suppressed(self):
        global deduplicate
        global exclude_service
        global exclude_message
        return not output_messages or \
               (collapse and self.circuit is not None and self.previous_circuit is not None) or \
               deduplicate and self.direction == IN and self.previous is not None and self.matches(self.previous) or \
               self.host_service and self.host_service[0].startswith(exclude_service) or \
               self.host_service and self.host_service[1].startswith(exclude_service) or \
               self.peer_service and self.peer_service[0].startswith(exclude_service) or \
               self.peer_service and self.peer_service[1].startswith(exclude_service) or \
               self.type.startswith(exclude_message)


def get_service(port):
    if port in service_map:
        return service_map[port]
    if 7700 <= port <= 7900:
        return "dispersy", "tracker"
    if 12000 <= port <= 13000:
        return "dispersy", "client"
    if 18000 <= port <= 19000:
        return "dht", "pymdht"
    if 20000 <= port <= 21000:
        return "torrent", "libtorrent"
    if 23000 <= port <= 24000:
        return "dht", "libtorrent"
    if 25000 <= port <= 26000:
        return "socks5", "server"
    return None


def detect_port_identity(identity, line):
    for expression, service in port_res:
        match = expression.search(line)
        if match:
            port = int(match.group(1))
            if service:
                service_map[port] = service
            elif expression.groups > 1:
                service_map[port] = match.group(2)
            identity_map[str(port)] = identity
            event = PortEvent(get_timestamp(line), identity, port, host_service=service)
            ordered_events.append(event)
            return event


def get_timestamp(line):
    match = timestamp_re.search(line)
    if not match:
        return None
    return int(float(match.group()) * 10000)


def emit_event(timestamp, me, other, direction, type, size, circuit):
    if other not in identity_map:
        print "ERROR: usage of identity element %s before it is opened by an identity" % other
        event = MessageEvent(timestamp, me, "port-%s" % other, direction, type, size, circuit)
    else:
        event = MessageEvent(timestamp, me, other, direction, type, size, circuit)

    ordered_events.append(event)
    return event


def process_message_line(identity, line):
    match = dispersy_event_re.search(line)
    if not match:
        return

    if match.group(7) is not None and match.group(7) != "":
        identity = int(match.group(7))

    emit_event(get_timestamp(line), identity, match.group(4), match.group(2), match.group(1), match.group(5),
               match.group(8))


def process_routing_line(identity, line):
    match = routing_event_out_re.search(line)
    if match:
        next_out_metadata[identity] = [int(match.group(1)) + TUNNEL_OVERHEAD, int(match.group(2)), None, match.group(4)]
        return

    match = routing_event_in_re.search(line)
    if match:
        next_out_metadata[identity] = [None, int(match.group(3)), None, None]
        return

    match = relay_event_re.search(line)
    if match:
        next_out_metadata[identity] = [None, int(match.group(2)), int(match.group(1)), None]


def ordered_log_generator():
    files = []
    lines = []
    identities = []

    def advance(index):
        lines[index] = files[index].readline()
        while lines[index] != "" and get_timestamp(lines[index]) is None:
            lines[index] = files[index].readline()
        if lines[index] == "":
            files[index].close()
            del files[index]
            del lines[index]
            del identities[index]

    for log_file in os.listdir(u'output'):
        if log_file.endswith((u'.out', u'.err')):
            files.append(open(os.path.join(u'output', log_file)))
            identities.append(int(log_file[-9:-4]))
            lines.append(None)
            advance(len(lines) - 1)

    while len(files) > 0:
        finger = -1
        for i in xrange(len(lines)):
            if finger == -1 or get_timestamp(lines[i]) < get_timestamp(lines[finger]):
                finger = i
        yield identities[finger], lines[finger]
        advance(finger)

with open(os.path.join(file_root, u"bootstraptribler.txt")) as boot:
    for line in boot:
        identity_map[line[-5:-1]] = "t%d" % len(identity_map)

for identity, line in ordered_log_generator():
    if "port" in line or "Socks" in line or " starting on " in line or "SOCKS5" in line:
        detect_port_identity(identity, line)
    if "<-" in line or "->" in line:
        process_message_line(identity, line)
    if "to end for circuit" in line or "Relay data from" in line or "Tunnel data to origin" in line:
        process_routing_line(identity, line)

transit = []

for event in ordered_events:
    if isinstance(event, PortEvent):
        continue
    is_internal = isinstance(event.host, int) and isinstance(event.peer, int) and event.peer_service[1] not in [
        "pymdht", "socks-client", "libtorrent"]
    if is_internal:
        match_event = None
        for message in transit:
            if event.matches(message):
                match_event = message
                break

        if match_event is not None:
            event.combine(match_event)
            transit.remove(match_event)
            if abs(event.time - match_event.time) > 30000:  # 3 seconds
                print "ERROR: message time traveled too far"
                transit.append(event)
            if match_event.direction == IN:
                # this is a real time traveler, the message is received before it is sent.
                event.time, match_event.time = match_event.time, event.time + 1
                event.set_next(match_event)
            else:
                match_event.set_next(event)
        else:
            transit.append(event)

# TODO: print warning for left in transit?
del transit


# we have to jump through some hoops to make the sort do the right thing in case of equivalent time codes
def sort_events(this, that):
    if not isinstance(this, PortEvent) and not isinstance(that, PortEvent) and this.time == that.time:
        if this.next == that:
            return -1
        elif that.next == this:
            return 1
        else:
            return 0
    else:
        return this.time - that.time

ordered_events.sort(cmp=sort_events)

# build tunnel direction map
# If we encounter a circuit routing event, it is not immediately clear what direction the circuit is going.
# But we need to know this in order to keep correct buffers about what is in transit on the circuits.
# So we first build a map of all circuit routing pairs and what direction they are. This starts by detecting a tunnel
# entry or exit (socks-private or socks-public) and denoting the correct direction. The inverse pair is by definition
# going the other way. When we then encounter a circuit routing pair, we can infer from existing uses of either element
# of the pair what direction the encountered pair is flowing.

tunnel_direction_map = {}
tunnel_transit = {}

for event in ordered_events:
    if isinstance(event, PortEvent) or event.circuit is None and event.previous_circuit is None:
        continue
    elif event.direction == IN and event.host_service[1] == "socks-private":
        event.circuit = -event.circuit
        tunnel_direction_map[(event.circuit, None)] = OUT  # first step of OUT
    elif event.direction == OUT and event.host_service[1] == "socks-private":
        tunnel_direction_map[(None, event.circuit)] = IN   # last step of IN
        event.circuit, event.previous_circuit = event.previous_circuit, event.circuit
    elif event.direction == IN and event.host_service[1] == "socks-public":
        event.circuit = -event.circuit
        tunnel_direction_map[(event.circuit, None)] = IN   # first step of IN
    elif event.direction == OUT and event.host_service[1] == "socks-public":
        tunnel_direction_map[(None, event.circuit)] = OUT  # last step of OUT
        event.circuit, event.previous_circuit = event.previous_circuit, event.circuit
    else:
        if event.previous_circuit is None:
            event.previous_circuit = -event.circuit
        elif event.circuit is None:
            event.circuit = -event.previous_circuit

        if (event.circuit, event.previous_circuit) in tunnel_direction_map:
            continue
        else:
            # Find occurrences of (event.circuit, <not prev_circuit>) If such a pair exists this pair goes the other way
            left_direction = [value for key, value in tunnel_direction_map.iteritems() if
                              key[0] == event.circuit and key[1] != event.previous_circuit]
            if len(left_direction) == 1:
                tunnel_direction_map[(event.circuit, event.previous_circuit)] = OUT if left_direction[0] == IN else IN
            elif len(left_direction) > 1:
                print "ERROR: Too many directions..."
            else:
                right_direction = [value for key, value in tunnel_direction_map.iteritems() if
                                   key[0] == event.previous_circuit and key[1] != event.circuit]
                if len(right_direction) == 1:
                    tunnel_direction_map[(event.circuit, event.previous_circuit)] = right_direction[0]
                elif len(right_direction) > 1:
                    print "ERROR: Too many directions..."


def push_tunnel_transit(circuit, direction, event):
    key = "%s %s" % (circuit, direction)
    transit = tunnel_transit.get(key, None)
    if transit:
        transit.append(event)
    else:
        tunnel_transit[key] = [event]


def pop_tunnel_transit(circuit, direction):
    key = "%s %s" % (circuit, direction)
    transit = tunnel_transit.get(key, None)
    ret = None
    if transit:
        ret = transit.pop(0)
        if len(transit) == 0:
            del tunnel_transit[key]
    return ret


for event in ordered_events:
    if isinstance(event, PortEvent) or event.circuit is None and event.previous_circuit is None:
        continue

    direction = tunnel_direction_map.get((event.circuit, event.previous_circuit), None)
    if direction is None:
        print "ERROR: No tunnel direction?!"
        continue

    if event.previous_circuit and event.previous is None:
        prev = pop_tunnel_transit(event.previous_circuit, direction)
        if prev and abs(event.time - prev.time) < 20000:
            prev.set_next(event)
    if event.circuit and event.next is None:
        push_tunnel_transit(event.circuit, direction, event)


# propagate tunnel destination
# If there is a message transit on a tunnel, it will be marked with its ultimate destination on the first hop
# So to make everything more clear, we mark all the messages of this transit with the ultimate destination
for event in ordered_events:
    if isinstance(event, PortEvent):
        continue
    if event.previous is None and event.next is not None:
        finger = event
        dest = None
        while finger is not None:
            if finger.dest is not None:
                dest = (finger.dest, finger.dest_service)
                break
            finger = finger.next
        if dest is None:
            continue
        finger = event
        while finger is not None:
            finger.dest = dest[0]
            finger.dest_service = dest[1]
            finger = finger.next

# The model is now complete, let's print some output

CSI = '\033['
FGRESET = CSI + '39m'
RED = '1'
GREEN = '2'
YELLOW = '3'
BLUE = '4'
MAGENTA = '5'
CYAN = '6'
LIGHT = '9'


def fg_color_generator():
    while True:
        for element in [RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN]:
            yield CSI + LIGHT + element + 'm'

fg = fg_color_generator()

output_slots = []
slot_chars = []
slot_colors = []

for event in ordered_events:
    if event.is_suppressed():
        continue

    line_color = FGRESET

    if isinstance(event, MessageEvent):
        # update the outputs with the next event
        for i in xrange(0, len(output_slots)):
            if output_slots[i] is not None and output_slots[i].next == event:
                output_slots[i] = event

        # if the event should be in output slots and it is not, find a free spot and add it, or create a new spot at the end
        if event.next is not None and event not in output_slots:
            index = None
            for i in xrange(0, max(len(slot_chars), len(output_slots))):
                if (len(output_slots) <= i or output_slots[i] is None) and (len(slot_chars) <= i or slot_chars[i] == ' '):
                    index = i
                    break
            if index is None:
                output_slots.append(event)
                slot_colors.append(next(fg))
                while len(slot_colors) > 1 and slot_colors[-2] == slot_colors[-1]:
                    slot_colors[-1] = next(fg)
            else:
                output_slots[index] = event
                slot_colors[index] = next(fg)
                while (index + 1 < len(slot_colors) and slot_colors[index + 1] == slot_colors[index]) or \
                        (index > 0 and slot_colors[index - 1] == slot_colors[index]):
                    slot_colors[index] = next(fg)

        # trim the array of outputs
        while len(output_slots) > 0 and output_slots[-1] is None:
            output_slots = output_slots[:-1]
            slot_colors = slot_colors[:-1]

    slot_chars = []
    for i in xrange(0, len(output_slots)):
        if output_slots[i] == event:
            line_color = slot_colors[i]
            if event.circuit is not None and event.previous_circuit is not None:
                if color:
                    slot_chars.append(slot_colors[i] + '+')
                else:
                    slot_chars.append('+')
            else:
                if color:
                    slot_chars.append(slot_colors[i] + '*')
                else:
                    slot_chars.append('*')
        elif output_slots[i] is not None:
            if color:
                slot_chars.append(slot_colors[i] + '|')
            else:
                slot_chars.append('|')
        else:
            slot_chars.append(' ')

    if isinstance(event, MessageEvent):
        # advance the output_slots past events that are suppressed.
        for i in xrange(0, len(output_slots)):
            while output_slots[i] and output_slots[i].next and output_slots[i].next.is_suppressed():
                output_slots[i] = output_slots[i].next

        # every line that is not needed any more is set cleared
        for i in xrange(0, len(output_slots)):
            if output_slots[i] is not None and output_slots[i].next is None:
                output_slots[i] = None

    if color:
        print "%s%s %s%s" % (line_color, event, " ".join(slot_chars), FGRESET)
    else:
        print "%s %s" % (event, " ".join(slot_chars))
