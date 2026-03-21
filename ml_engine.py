import joblib
import numpy as np
import json
import os
from datetime import datetime

FEATURE_ORDER = [
    'destination_port',
    'duration',
    'fwd_packet_count',
    'bwd_packet_count',
    'fwd_total_bytes',
    'bwd_total_bytes',
    'fwd_pack_len_mean',
    'fwd_pack_len_std',
    'bwd_pack_len_mean',
    'bwd_pack_len_std',
    'flow_bytes_sec',
    'Flow_Packets_sec',
    'flow_iat_mean',
    'flow_iat_std',
    'fwd_iat_total',
    'fwd_iat_mean',
    'fwd_iat_std',
    'bwd_iat_total',
    'bwd_iat_mean',
    'bwd_iat_std',
    'fwd_header_length',
    'bwd_header_length',
    'fwd_packets_sec',
    'bwd_packets_sec',
    'packet_length_mean',
    'packet_length_std',
    'variance',
    'fin_count',
    'syn_count',
    'rst_count',
    'psh_count',
    'ack_count',
    'urg_count',
    'down_up_ratio',
    'average',
    'avg_fwd_segment_size',
    'avg_bwd_segment_size',
    'init_win_fwd',
    'init_win_bwd',
    'act_data_pkt_fwd',
    'min_seg_size_forward',
    'active_mean',
    'active_std',
    'idle_mean',
    'idle_std',
]

def load_models(path: str):
    rf = joblib.load(path + "/models/random_forest_sur.pkl")
    iso = joblib.load(path + "/models/isolation_forest.pkl")
    scaler = joblib.load(path + "/models/scaler.pkl")
    encoder = joblib.load(path + "/models/label_encoder_sur.pkl")

    return rf, iso, scaler, encoder


def build_feature_vector(flow_statistics):
    feature_values = []
    for key in FEATURE_ORDER:
        feature_values.append(flow_statistics.get(key, 0))#!if the key is missing put 0 in it to not crash
    return np.array(feature_values)

 
#check if its normal or annormal atack 
def predict(scaler , iso ,rf ,encoder):
    
    iso_result = iso.predict(scaler)[0]
  
    if iso_result == 1:#*normal traffic
        return None
    #*anormal trafic pass to random forest
    else:
        probabilities = rf.predict_proba(scaler)[0]#get the proba of the atack
        predicted_index = int(np.argmax(probabilities))#finds the index of the largest probability and converts it to int
        attack_type = encoder.inverse_transform([predicted_index])[0]
        confidence = float(probabilities[predicted_index] * 100)

        return {
            'attack_type': attack_type,
            'confidence': confidence,
        }


def build_alert(flow_statistics, attack_type, confidence):
    if confidence > 90:
        severity = 'HIGH'
    elif 70 <= confidence <= 90:
        severity = 'MEDIUM'
    else:
        severity = 'LOW'

    return {
        'timestamp': datetime.utcnow().isoformat(),
        'attack_type': attack_type,
        'confidence': round(confidence, 2),
        'src_ip': flow_statistics['source_ip'],
        'dst_ip': flow_statistics['destination_ip'],
        'src_port': flow_statistics['source_port'],
        'dst_port': flow_statistics['destination_port'],
        'duration': round(flow_statistics['duration'], 4),
        'protocol': flow_statistics['protocol'],
        'severity': severity,
    }


def save_alert(alert):
    os.makedirs('alerts', exist_ok=True)
    with open('alerts/ids_log.json', 'a') as alert_file:
        alert_file.write(json.dumps(alert) + '\n')
