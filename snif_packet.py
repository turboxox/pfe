from scapy.all import *
from datetime import datetime
import sys

UDP_FLOW_TIMEOUT = 5
TCP_FLOW_TIMEOUT = 8
NETWORK_INTERFACE = "wlp0s20f3"

active_flows = {}
expired_flows = {}
flow_statistics = {}

PROTOCOLS = {6: 'TCP', 17: 'UDP'}

#clean each flow and delete it after the timeout
def clean_expired_flows(current_timestamp):
    flows_to_remove = []

    for flow_key, flow_data in active_flows.items():
        protocol = flow_data.get('protocol')
        idle_time = current_timestamp - flow_data['last_time']

        if (protocol == 'UDP' and idle_time > UDP_FLOW_TIMEOUT) or \
           (protocol == 'TCP' and idle_time > TCP_FLOW_TIMEOUT):
            flows_to_remove.append(flow_key)

    for flow_key in flows_to_remove:
        print(f"[FLOW ENDED] {flow_key}")

        flow_statistics[flow_key] = {
            'fwd_packets': active_flows[flow_key]['fwd_packets'],
            'bwd_packets': active_flows[flow_key]['bwd_packets'],
            'protocol': active_flows[flow_key]['protocol'],
            'total_bytes': active_flows[flow_key]['total_bytes'],
            'duration': active_flows[flow_key]['last_time'] - active_flows[flow_key]['start_time'],
            'source_ip': flow_key[0],
            'destination_ip': flow_key[1],
            'source_port': flow_key[2],
            'destination_port': flow_key[3],
            'natural_end': False
        }

        del active_flows[flow_key]

    return len(flows_to_remove)

def create_or_update_flow(flow_key, timestamp, packet_size, protocol, source_ip, source_port):
 
    if flow_key in active_flows:
        active_flows[flow_key]['last_time'] = timestamp
        active_flows[flow_key]['duration'] = timestamp - active_flows[flow_key]['start_time']
        active_flows[flow_key]['total_bytes'] += packet_size

        # Classify packet as forward or backward based on who initiated the flow
        if source_ip == active_flows[flow_key]['fwd_src_ip'] and source_port == active_flows[flow_key]['fwd_src_port']:
            active_flows[flow_key]['fwd_packets'] += 1
        else:
            active_flows[flow_key]['bwd_packets'] += 1

        total = active_flows[flow_key]['fwd_packets'] + active_flows[flow_key]['bwd_packets']
        print(f"[{protocol} UPDATE] {flow_key} - Fwd: {active_flows[flow_key]['fwd_packets']} Bwd: {active_flows[flow_key]['bwd_packets']} Total: {total}")
    else:
        active_flows[flow_key] = {
            'fwd_packets': 1,
            'bwd_packets': 0,
            'fwd_src_ip': source_ip,
            'fwd_src_port': source_port,
            'start_time': timestamp,
            'last_time': timestamp,
            'protocol': protocol,
            'total_bytes': packet_size,
            'duration': 0.0
        }

        print(f"[NEW {protocol}] {flow_key}")

#extract udp packets and added it to the flow tuple
def process_udp_packet(ip_packet, udp_packet, timestamp):
    source_ip = ip_packet.src
    destination_ip = ip_packet.dst
    source_port = udp_packet.sport
    destination_port = udp_packet.dport
    packet_size = ip_packet.len

    flow_key = (source_ip, destination_ip, source_port, destination_port, 'UDP')

    create_or_update_flow(flow_key, timestamp, packet_size, 'UDP', source_ip, source_port)

#extract tcp packets and added it to the flow tuple
def process_tcp_packet(ip_packet, tcp_packet, timestamp):
    
    source_ip = ip_packet.src
    destination_ip = ip_packet.dst
    source_port = tcp_packet.sport
    destination_port = tcp_packet.dport
    packet_size = ip_packet.len

    tcp_flags = tcp_packet.flags
    sequence_number = tcp_packet.seq
    ack_number = tcp_packet.ack
    window_size = tcp_packet.window

    flow_key = (source_ip, destination_ip, source_port, destination_port, 'TCP')

    create_or_update_flow(flow_key, timestamp, packet_size, 'TCP', source_ip, source_port)

    if tcp_flags & 0x01 or tcp_flags & 0x04:  # FIN or RST
        if flow_key in active_flows:
            print(f"[TCP CLOSED] {flow_key}")

    

def analyze_packet(packet):

    try:
        timestamp = packet.time

        clean_expired_flows(timestamp)

        if not packet.haslayer('IP'):
            return

        ip_packet = packet['IP']
        protocol_number = ip_packet.proto
        protocol_name = PROTOCOLS.get(protocol_number, 'OTHER')

        if packet.haslayer('UDP'):
            process_udp_packet(ip_packet, packet['UDP'], timestamp)

        elif packet.haslayer('TCP'):
            process_tcp_packet(ip_packet, packet['TCP'], timestamp)

        else:
            print(f"[IGNORED PROTOCOL] {protocol_name} - {ip_packet.src} -> {ip_packet.dst}")

    except Exception as error:
        print(f"[ERROR] {error}")

#print the flows
def display_final_statistics():
    
    print("\n" + "="*50)
    print("           FINAL REPORT")
    print("="*50)

    if active_flows:
        print(f"\nACTIVE FLOWS ({len(active_flows)}):")
        print("-" * 30)
        for flow_key, stats in active_flows.items():
            duration = stats['last_time'] - stats['start_time']
            print(f"\nFlow: {flow_key[0]}: SRCPORT : {flow_key[2]} -> {flow_key[1]}: DSTPORT : {flow_key[3]} ({flow_key[4]})")
            print(f"  Fwd Packets: {stats['fwd_packets']}")
            print(f"  Bwd Packets: {stats['bwd_packets']}")
            print(f"  Total Packets: {stats['fwd_packets'] + stats['bwd_packets']}")
            print(f"  Bytes: {stats['total_bytes']:,}")
            print(f"  Duration: {duration:.3f}s")

    if flow_statistics:
        print(f"\nENDED FLOWS ({len(flow_statistics)}):")
        print("-" * 30)
        for flow_key, stats in flow_statistics.items():
            print(f"\nFlow: {flow_key[0]}:{flow_key[2]} -> {flow_key[1]}:{flow_key[3]} ({flow_key[4]})")
            print(f"  Fwd Packets: {stats['fwd_packets']}")
            print(f"  Bwd Packets: {stats['bwd_packets']}")
            print(f"  Total Packets: {stats['fwd_packets'] + stats['bwd_packets']}")
            print(f"  Bytes: {stats['total_bytes']:,}")
            print(f"  Duration: {stats['duration']:.3f}s")

    print(f"\nTotal flows analyzed: {len(active_flows) + len(flow_statistics)}")

def main():
 
    print("="*80)
    print("    analyzer flow")
    print("="*80)
    print(f"name Interface: {NETWORK_INTERFACE}")
    print(f"Timeout UDP: {UDP_FLOW_TIMEOUT}s | TCP: {TCP_FLOW_TIMEOUT}s")
    print(f"Starting...")
    print("="*80)

    #snif packets 
    try:
        sniff(iface=NETWORK_INTERFACE, prn=analyze_packet , count = 100)

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    except Exception as error:
        print(f"\nError: {error}")
        print("Check the network interface and permissions")

    finally:
        display_final_statistics()

if __name__ == "__main__":
    main()