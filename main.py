import requests
import time

from fuzzy import fuzzy_refine
from yolo import detect_threat
from explainability import get_explanation

ESP_IP = "192.168.43.146"  # ← PUT YOUR ESP IP HERE

# -------- SESSION FOR PERSISTENT CONNECTION --------
session = requests.Session()

# -------- SENSOR FETCH --------
def get_sensor():
    try:
        res = session.get(f"http://{ESP_IP}", timeout=1.0)
        return res.json()
    except Exception as e:
        return None

# -------- CONSOLIDATED SYNC --------
def sync_with_esp(threat, pump):
    t_val = 1 if threat else 0
    p_val = 1 if pump else 0
    try:
        # One request updates both states simultaneously!
        session.get(f"http://{ESP_IP}/sync?t={t_val}&p={p_val}", timeout=0.8)
        print(f"🔄 Sync: Threat={'ON' if threat else 'OFF'}, Pump={'ON' if pump else 'OFF'}")
        return True
    except:
        print(f"❌ Sync failed")
        return False

# -------- SYSTEM STATE TRACKING --------
current_pump_on = False
pump_stop_time = 0
current_threat_active = False

# Smoothing counters
threat_frame_count = 0
safe_frame_count = 0

# -------- MAIN LOOP --------
print("\n" + "="*40)
print("      AgriSentinel Intelligence Cycle")
print("      (Consolidated Parallel Sync)")
print("="*40)

while True:
    loop_start = time.time()

    # 1️⃣ PERCEPTION: THREAT DETECTION
    raw_threat = detect_threat()
    
    # --- THREAT SMOOTHING ---
    if raw_threat:
        threat_frame_count += 1
        safe_frame_count = 0
    else:
        safe_frame_count += 1
        threat_frame_count = 0

    # Determine stable threat state
    new_threat_active = current_threat_active
    if threat_frame_count >= 2:
        new_threat_active = True
    elif safe_frame_count >= 10:
        new_threat_active = False

    # 2️⃣ DATA ACQUISITION
    data = get_sensor()
    if data is None:
        soil, temp, hum = 100, 25, 50 
    else:
        soil = data['soil']
        temp = data['temperature']
        hum = data['humidity']
        print(f"📊 Sensors: Soil={soil}%, Temp={temp}C, Hum={hum}%")

    # 3️⃣ DECISION: FUZZY LOGIC
    irr_need = fuzzy_refine(soil, temp, hum)
    
    # 4️⃣ EXECUTION: NON-BLOCKING LOGIC
    new_pump_on = current_pump_on

    # Check for pump STOP
    if current_pump_on and time.time() >= pump_stop_time:
        new_pump_on = False
        print("🛑 Pump Timer Finished")

    # Check for pump START
    if data is not None:
        if soil < 65 and not current_pump_on:
            pump_time = (irr_need / 100) * 15
            pump_time = max(2, min(pump_time, 20))
            new_pump_on = True
            pump_stop_time = time.time() + pump_time
            print(f"🌵 Soil Dry - Starting Pump for {pump_time:.1f}s")
        
        elif soil > 75 and current_pump_on:
            new_pump_on = False
            print("✅ Soil Saturated - Stopping Pump")

    # 5️⃣ SYNCHRONIZATION (The Parallel Fix)
    # Only send to ESP if either Threat OR Pump state changed
    if new_threat_active != current_threat_active or new_pump_on != current_pump_on:
        if sync_with_esp(new_threat_active, new_pump_on):
            current_threat_active = new_threat_active
            current_pump_on = new_pump_on

    # 6️⃣ COGNITIVE: EXPLAINABILITY
    if int(time.time()) % 5 == 0:
        explanation = get_explanation(soil, temp, hum, irr_need, current_threat_active)
        print(f"🤖 AI Reasoning: {explanation}")

    # Steady Loop
    elapsed = time.time() - loop_start
    time.sleep(max(0.1, 1.0 - elapsed))
