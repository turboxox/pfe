from scapy.all import *


interface_name="Intel(R) Wi-Fi 6 AX201 160MHz"

def show_ip(packet):
    if packet.haslayer(UDP):
        print(f"Source: {packet[IP].src} -> Dest: {packet[IP].dst}")

sniff(filter="UDP", prn=show_ip, count=10)
