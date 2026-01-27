from scapy.all import *


interface_name="Intel(R) Wi-Fi 6 AX201 160MHz"
def filter_packet(pkt):
    
    timestamp = pkt.time
    readable_time = datetime.fromtimestamp(timestamp)
    
    print(f"\n{'='*60}")
    print(f"Timestamp: {readable_time}")
    print(f"Raw time: {timestamp}")
    
    if pkt.haslayer('IP'):  
        print("src:", pkt['IP'].src,  
          "dst:", pkt['IP'].dst,
          "Protocol:", pkt['IP'].proto,
          "Total IP packet length:", pkt['IP'].len)  
    
    if pkt.haslayer('UDP'): 
        print("Source port:", pkt['UDP'].sport,
              "Destination port:", pkt['UDP'].dport,
              "UDP payload length:", pkt['UDP'].len)

sniff(iface=interface_name , prn=filter_packet)