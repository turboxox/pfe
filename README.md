README.md Content
Here is the complete README for your project:

ML-Powered Intrusion Detection System (IDS)
A real-time network intrusion detection system built with Python and Machine Learning. The system captures live network traffic, extracts 45 features per flow, and uses a two-stage ML pipeline (Isolation Forest + Random Forest) to classify attacks in real time.

Project Overview
This IDS was built as a final year engineering project (PFE). It bridges the gap between trained ML models and real-world live network traffic. The system detects 6 attack categories — DoS, DDoS, PortScan, Brute Force, Web Attack, and Bot — and generates structured JSON alerts for each detected threat.

Project Structure
pfe_project/
├── capture_script.py        # Live packet capture and flow feature extraction
├── ml_engine.py             # ML model loading, prediction, and alert generation
├── models/
│   ├── random_forest_sur.pkl
│   ├── isolation_forest.pkl
│   ├── scaler.pkl
│   └── label_encoder_sur.pkl
├── alerts/
│   └── ids_log.json         # Generated automatically at runtime
└── README.md

How It Works
The system operates in a 5-stage pipeline:
Stage 1 — Capture — Scapy sniffs live packets on the specified network interface and groups them into bidirectional flows using a 5-tuple key (src IP, dst IP, src port, dst port, protocol).
Stage 2 — Feature Extraction — When a flow ends (via timeout or FIN/RST), 45 features are computed from the flow including packet length statistics, inter-arrival times, TCP flag counts, flow speed metrics, header lengths, window sizes, and active/idle periods.
Stage 3 — Preprocessing — The 45 features are assembled into an ordered vector and normalized using the RobustScaler that was used during training.
Stage 4 — Two-Stage Detection — The Isolation Forest first checks if the flow is anomalous. If normal it is discarded. If anomalous the Random Forest classifies the specific attack type with a confidence score.
Stage 5 — Alert Generation — Detected attacks are saved as structured JSON alerts to alerts/ids_log.json with timestamp, attack type, confidence, source/destination IPs, ports, duration, protocol, and severity level.

Requirements
Install dependencies with:
pip install scapy scikit-learn joblib numpy
Python 3.8 or higher is required.

Configuration
At the top of capture_script.py you can configure:
NETWORK_INTERFACE — set this to your network interface name. On Linux use ip a to find it. Common values are eth0, wlan0, wlp0s20f3.
TCP_FLOW_TIMEOUT — seconds of inactivity before a TCP flow is considered ended. Default is 8.
UDP_FLOW_TIMEOUT — seconds of inactivity before a UDP flow is considered ended. Default is 5.
ACTIVITY_THRESHOLD — seconds of silence that separates active bursts. Default is 1.0.

Usage
Step 1 — Place your trained model files inside the models/ folder. You need four files: random_forest_sur.pkl, isolation_forest.pkl, scaler.pkl, and label_encoder_sur.pkl.
Step 2 — Set your network interface in capture_script.py.
Step 3 — Run the system with root permissions (required for packet capture):
sudo python3 capture_script.py
Step 4 — The system will start capturing traffic and printing flow updates to the console. When an attack is detected you will see:
[DETECTED] DoS | src=192.168.1.42 -> dst=10.0.0.1 | confidence=91.3%
Step 5 — All alerts are saved automatically to alerts/ids_log.json. Each line is one alert in JSON format.

Alert Format
Each alert in ids_log.json looks like this:
json{
  "timestamp": "2026-03-22T10:59:22.780196",
  "attack_type": "DoS",
  "confidence": 91.30,
  "src_ip": "192.168.1.42",
  "dst_ip": "10.0.0.1",
  "src_port": 52197,
  "dst_port": 80,
  "duration": 12.4312,
  "protocol": "TCP",
  "severity": "HIGH"
}
Severity levels are HIGH (confidence above 90%), MEDIUM (70% to 90%), and LOW (below 70%).

Detected Attack Types
Attack TypeDescriptionDoSDenial of Service — flooding a target to exhaust resourcesDDoSDistributed Denial of Service — same but from multiple sourcesPortScanSystematic probing of ports to find open servicesBrute ForceRepeated login attempts on SSH, FTP, or HTTPWeb AttackSQL injection, XSS, or other HTTP-based attacksBotAutomated malicious traffic from compromised machines

Dataset
The ML models were trained on the CICIDS2017 dataset — a standard benchmark in network intrusion detection research containing labeled samples of both normal and attack traffic across multiple attack categories.

Known Limitations
Encrypted traffic (HTTPS/TLS) hides payload content so only metadata and header features are analyzed. The model was trained on 2017 lab traffic and may produce false positives on modern real-world networks due to dataset shift. Retraining on traffic from the target network is recommended for production use.

