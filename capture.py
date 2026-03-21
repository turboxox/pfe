from scapy.all import *
from datetime import datetime
import sys
import statistics

UDP_FLOW_TIMEOUT = 5
TCP_FLOW_TIMEOUT = 8
NETWORK_INTERFACE = "wlp0s20f3"
ACTIVITY_THRESHOLD = 1.0

active_flows = {}
expired_flows = {}
flow_statistics = {}
FEATURE_ORDER ={}

PROTOCOLS = {6: 'TCP', 17: 'UDP'}


def timestamps_to_gaps(timestamps):
    if len(timestamps) < 2:
        return []
    gaps = []
    for i in range(1, len(timestamps)):
        gaps.append(timestamps[i] - timestamps[i - 1])
    return gaps


def split_active_idle_periods(timestamps, threshold):
    if not timestamps:
        return [], []

    active_times = []
    idle_times = []
    current_active_duration = 0.0

    for i in range(1, len(timestamps)):
        gap = timestamps[i] - timestamps[i - 1]
        if gap > threshold:
            active_times.append(current_active_duration)
            idle_times.append(gap)
            current_active_duration = 0.0
        else:
            current_active_duration += gap

    active_times.append(current_active_duration)
    return active_times, idle_times

#!clean each flow and delete it after the timeout
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
        all_gaps = timestamps_to_gaps(active_flows[flow_key]['all_timestamps'])
        fwd_gaps = timestamps_to_gaps(active_flows[flow_key]['fwd_timestamps'])
        bwd_gaps = timestamps_to_gaps(active_flows[flow_key]['bwd_timestamps'])
        active_times, idle_times = split_active_idle_periods(active_flows[flow_key]['all_timestamps'], ACTIVITY_THRESHOLD)

        fwd_sizes = active_flows[flow_key]['fwd_packet_sizes']
        bwd_sizes = active_flows[flow_key]['bwd_packet_sizes']
        all_sizes = fwd_sizes + bwd_sizes

        #copy summary before del
        flow_statistics[flow_key] = {
            # 'protocol': active_flows[flow_key]['protocol'],
            'duration': active_flows[flow_key]['last_time'] - active_flows[flow_key]['start_time'],
            # 'source_ip': flow_key[0],
            # 'destination_ip': flow_key[1],
            # 'source_port': flow_key[2],
            'destination_port': flow_key[3],
            # 'natural_end': False,
            'fwd_packet_count': active_flows[flow_key]['fwd_packet_count'],
            'bwd_packet_count': active_flows[flow_key]['bwd_packet_count'],
            # 'fwd_pack_len_max':max(active_flows[flow_key]['fwd_packet_sizes']) if active_flows[flow_key]['fwd_packet_sizes'] else 0,#we add the if bc it could crashout if the list is empty
            # 'fwd_pack_len_min':min(active_flows[flow_key]['fwd_packet_sizes']) if active_flows[flow_key]['fwd_packet_sizes'] else 0,
            'fwd_pack_len_mean':statistics.mean(active_flows[flow_key]['fwd_packet_sizes']) if active_flows[flow_key]['fwd_packet_sizes'] else 0,
            'fwd_pack_len_std':statistics.stdev(active_flows[flow_key]['fwd_packet_sizes']) if len(active_flows[flow_key]['fwd_packet_sizes']) > 1 else 0, #!whenever std is close to 0 its maybe an atack
            # 'bwd_pack_len_max':max(active_flows[flow_key]['bwd_packet_sizes']) if active_flows[flow_key]['bwd_packet_sizes'] else 0,
            # 'bwd_pack_len_min':min(active_flows[flow_key]['bwd_packet_sizes'])if active_flows[flow_key]['bwd_packet_sizes'] else 0,
            'bwd_pack_len_mean':statistics.mean(active_flows[flow_key]['bwd_packet_sizes']) if active_flows[flow_key]['bwd_packet_sizes'] else 0,
            'bwd_pack_len_std':statistics.stdev(active_flows[flow_key]['bwd_packet_sizes']) if len(active_flows[flow_key]['bwd_packet_sizes']) > 1 else 0,
            # 'min_packet_len':min(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes']) 
            #                  if len(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes']) else 0,
            # 'max_packet_len':max(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes']) 
            #                  if len(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes']) else 0,
            'packet_length_mean':statistics.mean(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes']) 
                                if active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes'] else 0,
            'packet_length_std':statistics.stdev(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes']) 
                                if len(active_flows[flow_key]['fwd_packet_sizes']) > 1  and len(active_flows[flow_key]['bwd_packet_sizes']) > 1  else 0,
            'variance':statistics.variance(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes'])
                        if len(active_flows[flow_key]['fwd_packet_sizes']) > 1  and len(active_flows[flow_key]['bwd_packet_sizes']) > 1  else 0,
            'average':statistics.mean(active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes']) 
                                if active_flows[flow_key]['fwd_packet_sizes']+active_flows[flow_key]['bwd_packet_sizes'] else 0,
            'flow_bytes_sec':sum(all_sizes) / active_flows[flow_key]['duration'] if active_flows[flow_key]['duration'] else 0 ,
            'Flow_Packets_sec':len(all_sizes) / active_flows[flow_key]['duration'] if active_flows[flow_key]['duration'] else 0,
            'fwd_packets_sec':active_flows[flow_key]['fwd_packet_count'] / active_flows[flow_key]['duration'] if active_flows[flow_key]['duration'] else 0,
            'bwd_packets_sec': active_flows[flow_key]['bwd_packet_count'] / active_flows[flow_key]['duration'] if active_flows[flow_key]['duration'] else 0,
            'flow_iat_mean': statistics.mean(all_gaps) if all_gaps else 0,
            'flow_iat_std': statistics.stdev(all_gaps) if len(all_gaps) > 1 else 0,
            # 'flow_iat_max': max(all_gaps) if all_gaps else 0,
            # 'flow_iat_min': min(all_gaps) if all_gaps else 0,
            'fwd_iat_total': sum(fwd_gaps),
            'fwd_iat_mean': statistics.mean(fwd_gaps) if fwd_gaps else 0,
            'fwd_iat_std': statistics.stdev(fwd_gaps) if len(fwd_gaps) > 1 else 0,
            # 'fwd_iat_max': max(fwd_gaps) if fwd_gaps else 0,
            # 'fwd_iat_min': min(fwd_gaps) if fwd_gaps else 0,
            'bwd_iat_total': sum(bwd_gaps),
            'bwd_iat_mean': statistics.mean(bwd_gaps) if bwd_gaps else 0,
            'bwd_iat_std': statistics.stdev(bwd_gaps) if len(bwd_gaps) > 1 else 0,
            # 'bwd_iat_max': max(bwd_gaps) if bwd_gaps else 0,
            # 'bwd_iat_min': min(bwd_gaps) if bwd_gaps else 0,
            'fin_count': active_flows[flow_key]['fin_count'],
            'syn_count': active_flows[flow_key]['syn_count'],
            'rst_count': active_flows[flow_key]['rst_count'],
            'psh_count': active_flows[flow_key]['psh_count'],
            'ack_count': active_flows[flow_key]['ack_count'],
            'urg_count': active_flows[flow_key]['urg_count'],
            # 'cwe_count': active_flows[flow_key]['cwe_count'],
            # 'ece_count': active_flows[flow_key]['ece_count'],
            # 'fwd_psh_count': active_flows[flow_key]['fwd_psh_count'],
            # 'fwd_urg_count': active_flows[flow_key]['fwd_urg_count'],
            'fwd_header_length': active_flows[flow_key]['fwd_header_length'],
            'bwd_header_length': active_flows[flow_key]['bwd_header_length'],
            'avg_fwd_segment_size': statistics.mean(active_flows[flow_key]['fwd_segment_sizes']) if active_flows[flow_key]['fwd_segment_sizes'] else 0,
            'avg_bwd_segment_size': statistics.mean(active_flows[flow_key]['bwd_segment_sizes']) if active_flows[flow_key]['bwd_segment_sizes'] else 0,
            # 'subflow_fwd_packets': active_flows[flow_key]['fwd_packet_count'],
            'fwd_total_bytes': active_flows[flow_key]['fwd_total_bytes'],
            # 'subflow_bwd_packets': active_flows[flow_key]['bwd_packet_count'],
            'bwd_total_bytes': active_flows[flow_key]['bwd_total_bytes'],
            'init_win_fwd': active_flows[flow_key]['init_win_fwd'],
            'init_win_bwd': active_flows[flow_key]['init_win_bwd'],
            'act_data_pkt_fwd': active_flows[flow_key]['act_data_pkt_fwd'],
            'min_seg_size_forward': min(active_flows[flow_key]['fwd_tcp_header_sizes']) if active_flows[flow_key]['fwd_tcp_header_sizes'] else 0,
            'down_up_ratio': active_flows[flow_key]['bwd_total_bytes'] / active_flows[flow_key]['fwd_total_bytes'] if active_flows[flow_key]['fwd_total_bytes'] else 0,
            'active_mean': statistics.mean(active_times) if active_times else 0,
            'active_std': statistics.stdev(active_times) if len(active_times) > 1 else 0,
            # 'active_max': max(active_times) if active_times else 0,
            # 'active_min': min(active_times) if active_times else 0,
            'idle_mean': statistics.mean(idle_times) if idle_times else 0,
            'idle_std': statistics.stdev(idle_times) if len(idle_times) > 1 else 0,
            # 'idle_max': max(idle_times) if idle_times else 0,
            # 'idle_min': min(idle_times) if idle_times else 0,
        }

        del active_flows[flow_key]

    return len(flows_to_remove)

#!heart of the code here is where i creat flow or update it
def create_or_update_flow(flow_key, timestamp, packet_size, protocol, source_ip, source_port, window_size):
 
    if flow_key in active_flows:
        active_flows[flow_key]['last_time'] = timestamp
        active_flows[flow_key]['duration'] = timestamp - active_flows[flow_key]['start_time']
        active_flows[flow_key]['all_timestamps'].append(timestamp)

        #check if the flow is forw or backw
        if source_ip == active_flows[flow_key]['fwd_src_ip'] and source_port == active_flows[flow_key]['fwd_src_port']:
            active_flows[flow_key]['fwd_packet_count'] += 1
            active_flows[flow_key]['fwd_packet_sizes'].append(packet_size)
            active_flows[flow_key]['fwd_total_bytes'] += packet_size
            active_flows[flow_key]['fwd_timestamps'].append(timestamp)
        else:
            if active_flows[flow_key]['bwd_packet_count'] == 0:
                active_flows[flow_key]['init_win_bwd'] = window_size
            active_flows[flow_key]['bwd_packet_count'] += 1
            active_flows[flow_key]['bwd_packet_sizes'].append(packet_size)
            active_flows[flow_key]['bwd_total_bytes'] += packet_size
            active_flows[flow_key]['bwd_timestamps'].append(timestamp)

        total = active_flows[flow_key]['fwd_packet_count'] + active_flows[flow_key]['bwd_packet_count']
        print(f"[{protocol} UPDATE] {flow_key} - Fwd: {active_flows[flow_key]['fwd_packet_count']} |||  Bwd: {active_flows[flow_key]['bwd_packet_count']} Total: {total}")
    else:
        active_flows[flow_key] = {
            'fwd_packet_count': 1,
            'bwd_packet_count': 0,
            'fwd_src_ip': source_ip,
            'fwd_src_port': source_port,
            'start_time': timestamp,
            'last_time': timestamp,
            'protocol': protocol,
            'fwd_packet_sizes': [packet_size],
            'bwd_packet_sizes': [],
            'fwd_total_bytes': packet_size,
            'bwd_total_bytes': 0,
            'duration': 0.0,
            'all_timestamps': [],
            'fwd_timestamps': [],
            'bwd_timestamps': [],
            'fin_count': 0,
            'syn_count': 0,
            'rst_count': 0,
            'psh_count': 0,
            'ack_count': 0,
            'urg_count': 0,
            'cwe_count': 0,
            'ece_count': 0,
            'fwd_psh_count': 0,
            'fwd_urg_count': 0,
            'fwd_header_length': 0,
            'bwd_header_length': 0,
            'fwd_segment_sizes': [],
            'bwd_segment_sizes': [],
            'init_win_fwd': 0,
            'init_win_bwd': 0,
            'act_data_pkt_fwd': 0,
            'fwd_tcp_header_sizes': []
        }

        active_flows[flow_key]['init_win_fwd'] = window_size

        active_flows[flow_key]['all_timestamps'].append(timestamp)
        active_flows[flow_key]['fwd_timestamps'].append(timestamp)

        print(f"[NEW {protocol}] {flow_key}")

#extract udp packets and added it to the flow tuple
def process_udp_packet(ip_packet, udp_packet, timestamp):
    source_ip = ip_packet.src
    destination_ip = ip_packet.dst
    source_port = udp_packet.sport
    destination_port = udp_packet.dport
    packet_size = ip_packet.len

    flow_key = (source_ip, destination_ip, source_port, destination_port, 'UDP')
    reverse_key = (destination_ip, source_ip, destination_port, source_port, 'UDP')

    # if the reverse flow already exists, use that key so this packet counts as backward
    if reverse_key in active_flows:
        flow_key = reverse_key

    create_or_update_flow(flow_key, timestamp, packet_size, 'UDP', source_ip, source_port, 0)

    ip_header_len = ip_packet.ihl * 4
    udp_header_len = 8
    total_header_len = ip_header_len + udp_header_len
    segment_size = packet_size - total_header_len

    if source_ip == active_flows[flow_key]['fwd_src_ip'] and source_port == active_flows[flow_key]['fwd_src_port']:
        active_flows[flow_key]['fwd_header_length'] += total_header_len
        active_flows[flow_key]['fwd_segment_sizes'].append(segment_size)
    else:
        active_flows[flow_key]['bwd_header_length'] += total_header_len
        active_flows[flow_key]['bwd_segment_sizes'].append(segment_size)

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
    reverse_key = (destination_ip, source_ip, destination_port, source_port, 'TCP')

    # if the reverse flow already exists, use that key so this packet counts as backward
    if reverse_key in active_flows:
        flow_key = reverse_key

    create_or_update_flow(flow_key, timestamp, packet_size, 'TCP', source_ip, source_port, tcp_packet.window)

    ip_header_len = ip_packet.ihl * 4
    tcp_header_len = tcp_packet.dataofs * 4
    total_header_len = ip_header_len + tcp_header_len
    segment_size = packet_size - total_header_len

    if source_ip == active_flows[flow_key]['fwd_src_ip'] and source_port == active_flows[flow_key]['fwd_src_port']:
        active_flows[flow_key]['fwd_header_length'] += total_header_len
        active_flows[flow_key]['fwd_segment_sizes'].append(segment_size)
        active_flows[flow_key]['fwd_tcp_header_sizes'].append(tcp_header_len)
        if segment_size > 0:
            active_flows[flow_key]['act_data_pkt_fwd'] += 1
    else:
        active_flows[flow_key]['bwd_header_length'] += total_header_len
        active_flows[flow_key]['bwd_segment_sizes'].append(segment_size)

    if tcp_flags & 0x01:
        active_flows[flow_key]['fin_count'] += 1
    if tcp_flags & 0x02:
        active_flows[flow_key]['syn_count'] += 1
    if tcp_flags & 0x04:
        active_flows[flow_key]['rst_count'] += 1
    if tcp_flags & 0x08:
        active_flows[flow_key]['psh_count'] += 1
    if tcp_flags & 0x10:
        active_flows[flow_key]['ack_count'] += 1
    if tcp_flags & 0x20:
        active_flows[flow_key]['urg_count'] += 1
    if tcp_flags & 0x40:
        active_flows[flow_key]['ece_count'] += 1
    if tcp_flags & 0x80:
        active_flows[flow_key]['cwe_count'] += 1

    if source_ip == active_flows[flow_key]['fwd_src_ip']:
        if tcp_flags & 0x08:
            active_flows[flow_key]['fwd_psh_count'] += 1
        if tcp_flags & 0x20:
            active_flows[flow_key]['fwd_urg_count'] += 1

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

#*print the flows
def display_final_statistics():
    
    print("\n" + "="*50)
    print("           FINAL REPORT")
    print("="*50)

    #!printing active flows
    if active_flows:
        print(f"\nACTIVE FLOWS ({len(active_flows)}):")
        print("-" * 30)
        for flow_key, stats in active_flows.items():
            duration = stats['last_time'] - stats['start_time']
            print(f"\nFlow: {flow_key[0]}: SRCPORT : {flow_key[2]} -> {flow_key[1]}: DSTPORT : {flow_key[3]} ({flow_key[4]})")
            print(f"  Fwd Packets: {stats['fwd_packet_count']}")
            print(f"  Bwd Packets: {stats['bwd_packet_count']}")
            print(f"  Total Packets: {stats['fwd_packet_count'] + stats['bwd_packet_count']}")
            print(f"  Duration: {duration:.3f}s")


    #!printing ending flow
    if flow_statistics:
        print(f"\nENDED FLOWS ({len(flow_statistics)}):")
        print("-" * 30)
        for flow_key, stats in flow_statistics.items():
            print(f"\nFlow: {flow_key[0]}:{flow_key[2]} -> {flow_key[1]}:{flow_key[3]} ({flow_key[4]})")
            print(f"  Fwd Packets: {stats['fwd_packet_count']}")
            print(f"  Bwd Packets: {stats['bwd_packet_count']}")
            print(f"  Total Packets: {stats['fwd_packet_count'] + stats['bwd_packet_count']}")
            print(f"  Duration: {stats['duration']:.3f}s")
            print(f"  Fwd_pack_len_mean is :{stats['fwd_pack_len_mean']}")
            print(f"  Fwd_pack_len_std is : {stats['fwd_pack_len_std']}")
            print(f"  Bwd_pack_len_mean is :{stats['bwd_pack_len_mean']}")
            print(f"  Bwd_pack_len_std is : {stats['bwd_pack_len_std']}")
            # print(f"  min_packet_len : {stats['min_packet_len']}")
            # print(f"  max_packet_len :{stats['max_packet_len']}")
            print(f"  packet_length_mean :{stats['packet_length_mean']}")
            print(f"  packet_length_std :{stats['packet_length_std']}")
            print(f"  variance is :{stats['variance']}")
            print(f"  average is : {stats['average']}")
            print(f"  flow_bytes_sec:{stats['flow_bytes_sec']}")
            print(f"  Flow_Packets_sec:{stats['Flow_Packets_sec']}")
            print(f"  fwd_packets_sec:{stats['fwd_packets_sec']}")  
            print(f"  bwd_packets_sec:{stats['bwd_packets_sec']}")
            print(f"  fin_count:{stats['fin_count']}")
            print(f"  syn_count:{stats['syn_count']}")
            print(f"  rst_count:{stats['rst_count']}")
            print(f"  psh_count:{stats['psh_count']}")
            print(f"  ack_count:{stats['ack_count']}")
            print(f"  urg_count:{stats['urg_count']}")
            # print(f"  cwe_count:{stats['cwe_count']}")
            # print(f"  ece_count:{stats['ece_count']}")
            # print(f"  fwd_psh_count:{stats['fwd_psh_count']}")
            # print(f"  fwd_urg_count:{stats['fwd_urg_count']}")
            print(f"  fwd_header_length:{stats['fwd_header_length']}")
            print(f"  bwd_header_length:{stats['bwd_header_length']}")
            print(f"  avg_fwd_segment_size:{stats['avg_fwd_segment_size']}")
            print(f"  avg_bwd_segment_size:{stats['avg_bwd_segment_size']}")
            # print(f"  subflow_fwd_packets:{stats['subflow_fwd_packets']}")
            print(f"  fwd_total_bytes:{stats['fwd_total_bytes']}")
            # print(f"  subflow_bwd_packets:{stats['subflow_bwd_packets']}")
            print(f"  bwd_total_bytes:{stats['bwd_total_bytes']}")
            print(f"  init_win_fwd:{stats['init_win_fwd']}")
            print(f"  init_win_bwd:{stats['init_win_bwd']}")
            print(f"  act_data_pkt_fwd:{stats['act_data_pkt_fwd']}")
            print(f"  min_seg_size_forward:{stats['min_seg_size_forward']}")
            print(f"  down_up_ratio:{stats['down_up_ratio']}")
            
    
    
    print(f"\nTotal flows analyzed: {len(active_flows) + len(flow_statistics)}")

def main():
 
    print("="*80)
    print("    analyzer flow")
    print("="*80)
    print(f"name Interface: {NETWORK_INTERFACE}")
    print(f"Timeout UDP: {UDP_FLOW_TIMEOUT}s | TCP: {TCP_FLOW_TIMEOUT}s")
    print(f"Starting...")
    print("="*80)

    
    #*snif packets 
    try:
        sniff(iface=NETWORK_INTERFACE, prn=analyze_packet )

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    except Exception as error:
        print(f"\nError: {error}")
        print("Check the network interface and permissions")

    finally:
        display_final_statistics()

if __name__ == "__main__":
    main()
