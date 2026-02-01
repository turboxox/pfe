from scapy.all import *
from datetime import datetime


flows ={}
udp_flow_timeout = 30
tcp_flow_timeout = 60
interface_name="Intel(R) Wi-Fi 6 AX201 160MHz"

protocol_names = {6: 'TCP', 17: 'UDP'}

def filter_packet(pkt):
    timestamp = pkt.time 
    expired_flows = []
    # Check each flow and remove expired ones
    for flow_key, flow_data in flows.items():
        protocol = flow_data.get('protocol')
        if protocol == 'UDP' and timestamp - flow_data['last_time'] > udp_flow_timeout:
            expired_flows.append(flow_key)
        elif protocol == 'TCP' and timestamp - flow_data['last_time'] > tcp_flow_timeout:
            expired_flows.append(flow_key)

    for flow_key in expired_flows:
        print(f"[flow ended after timeout] {flow_key}")  
        del flows[flow_key]
    
    #checking if the pakcet has Ip first
    if pkt.haslayer('IP'):  
            src=pkt['IP'].src
            dst =pkt['IP'].dst
            protocol_num = pkt['IP'].proto
            protocol_name = protocol_names.get(protocol_num, 'OTHER')
            tipl =pkt['IP'].len
        
            #check if the packet has udp
            if pkt.haslayer('UDP'): 
                sport =pkt['UDP'].sport
                dport=pkt['UDP'].dport
                flow_key=(src , dst,sport,dport,protocol_name)#creating the tuple that has the flow information
            
                if flow_key in flows :
                    flows[flow_key]['packets']+=1
                    flows[flow_key]['last_time']=timestamp
                else:
                    flows[flow_key]={
                        'packets':1,
                        'start_time':timestamp,
                        'last_time':timestamp,
                        'protocol': 'UDP'
                    }
                print(f"flow{flow_key}") 
                print(f"totale pakctes in this flow:{flows[flow_key]["packets"]}")   
            elif pkt.haslayer('TCP'):
                tcpsport = pkt['TCP'].sport
                tcpdport = pkt['TCP'].dport
                tcpflags =pkt['TCP'].flags
                tcpseq =pkt['TCP'].seq
                tcpack = pkt['TCP'].ack
                tcpwindow = pkt['TCP'].window
                flow_key =(src,dst,tcpsport,tcpdport,protocol_name)

                if flow_key in flows :
                    flows[flow_key]['packets']+=1
                    flows[flow_key]['last_time']=timestamp
                else:
                    flows[flow_key]={
                        'packets':1,
                        'start_time':timestamp,
                        'last_time':timestamp,
                        'protocol': 'TCP'
                    }
                print(f"flow{flow_key}") 
                print(f"totale pakctes in this flow:{flows[flow_key]["packets"]}")   
sniff(iface=interface_name , prn=filter_packet )
print("\n"+"="*10)
print("all flow")
for flow, stats in flows.items():
    print(f"\nFlow: {flow}")
    print(f"  Packets: {stats['packets']}")
    print(f"  Duration: {stats['last_time'] - stats['start_time']:.3f} seconds")