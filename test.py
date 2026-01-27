from scapy.all import *


p=sniff(filter="udp", count=1, iface="Intel(R) Wi-Fi 6 AX201 160MHz")
p[0].show()