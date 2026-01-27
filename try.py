from scapy.all import *

def handle_packet(pkt):
    if pkt.haslayer('IP'):
        print(
            pkt['IP'].src,
            "→",
            pkt['IP'].dst       
        )

sniff(prn=handle_packet, store=False, count=10)