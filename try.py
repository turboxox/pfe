from scapy.all import *
from datetime import datetime


flows ={}
flow_timeout = 5
interface_name="Intel(R) Wi-Fi 6 AX201 160MHz"
def filter_packet(pkt):
    timestamp = pkt.time  
    expired_flows = []

    for flow_key, flow_data in flows.items():
        if timestamp - flow_data['last_time'] > flow_timeout:
            expired_flows.append(flow_key)

    for flow_key in expired_flows:
        print(f"[flow ended bc it passed 5 sec] {flow_key}")  
        del flows[flow_key]

    if pkt.haslayer('IP'):  
        src=pkt['IP'].src
        dst =pkt['IP'].dst
        protocol= pkt['IP'].proto
        tipl =pkt['IP'].len
    

        if pkt.haslayer('UDP'): 
            sport =pkt['UDP'].sport
            dport=pkt['UDP'].dport
            proto_name ="UDP"        
            flow_key=(src , dst,sport,dport,proto_name)
        
            if flow_key in flows :
                flows[flow_key]['packets']+=1
                flows[flow_key]['last_time']=timestamp
            else:
                flows[flow_key]={
                    'packets':1,
                    'start_time':timestamp,
                    'last_time':timestamp
                }
            print(f"flow{flow_key}") 
            print(f"totale pakctes in this flow:{flows[flow_key]["packets"]}")   

sniff(iface=interface_name , prn=filter_packet , count=100)
print("\n"+"="*10)
print("all flow")
for flow, stats in flows.items():
    print(f"\nFlow: {flow}")
    print(f"  Packets: {stats['packets']}")
    print(f"  Duration: {stats['last_time'] - stats['start_time']:.3f} seconds")