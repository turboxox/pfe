from scapy.all import *

p=sniff(count=10)
print(p)
p[2].show()