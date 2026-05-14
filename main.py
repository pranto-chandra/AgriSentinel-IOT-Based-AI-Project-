import requests
import time

from fuzzy import fuzzy_refine
from yolo import detect_threat
from explainability import get_explanation

ESP_IP = "192.168.43.146"  # ← PUT YOUR ESP IP HERE

# -------- SESSION FOR PERSISTENT CONNECTION --------
session = requests.Session()

# -------- CONSOLIDATED COMMUNICATION --------
def esp_sync(threat, pump, ai_msg=None):
    """
    Sends states to ESP and returns latest sensor data in one request.
    """
    params = {
        't': 1 if threat else 0,
        'p': 1 if pump else 0
    }
    
    if ai_msg:
        params['msg'] = ai_msg
    
    url = f"http://{ESP_IP}/sync"
    
    try:
        # requests handles URL encoding of params automatically
        res = session.get(url, params=params, timeout=2.0)
        data = res.json()
        return data
    except Exception as e:
        return None

# -------- SYSTEM STATE TRACKING --------
current_pump_on = False
pump_stop_time = 0
current_threat_active = False

# Smoothing counters
threat_frame_count = 0
safe_frame_count = 0

# Initialize sensor variables with neutral values
soil, temp, hum = 70, 25, 50

# -------- MAIN LOOP --------
print("\n" + "="*40)
print("      AgriSentinel Intelligence Cycle")
print("      (Consolidated High-Speed Sync)")
print("="*40)

# Global tracking for AI
last_explanation = "অপেক্ষা করা হচ্ছে..."

while True:
    loop_start = time.time()

    # 1️⃣ PERCEPTION: THREAT DETECTION
    raw_threat = detect_threat()
    
    if raw_threat is None:
        print("⚠️ Camera issue - skipping frame")
        time.sleep(0.5)
        continue
    
    # Smoothing
    if raw_threat:
        threat_frame_count += 1
        safe_frame_count = 0
    else:
        safe_frame_count += 1
        threat_frame_count = 0

    new_threat_active = current_threat_active
    if threat_frame_count >= 2:
        new_threat_active = True
    elif safe_frame_count >= 1: # Instant reset when threat moves
        new_threat_active = False

    # 2️⃣ COGNITIVE: AI REASONING (Every 5s)
    current_explanation = None
    if int(time.time()) % 5 == 0:
        # Calculate potential pump time for AI
        irr_need = fuzzy_refine(soil, temp, hum)
        calc_pump_time = (irr_need / 100) * 15
        calc_pump_time = max(2, min(calc_pump_time, 20))
        if soil >= 75: calc_pump_time = 0
        
        last_explanation = get_explanation(soil, temp, hum, calc_pump_time, new_threat_active)
        current_explanation = last_explanation # Send this loop
        print(f"🤖 AI Reasoning: {last_explanation}")

    # 3️⃣ SYNCHRONIZATION & DATA FETCH (The Master Call)
    # We always call this to get sensor data, even if state hasn't changed
    data = esp_sync(new_threat_active, current_pump_on, current_explanation)

    if data is not None:
        soil = data['soil']
        temp = data['temperature']
        hum = data['humidity']
        # Update our tracking of what the ESP thinks
        current_threat_active = new_threat_active
        print(f"📊 Sensors: Soil={soil}%, Temp={temp}C, Hum={hum}% | Sync: OK")
    else:
        print("⚠️ Sync failed - ESP unreachable")

    # 4️⃣ DECISION: FUZZY LOGIC (Based on fresh sync data)
    irr_need = fuzzy_refine(soil, temp, hum)
    calc_pump_time = (irr_need / 100) * 15
    calc_pump_time = max(2, min(calc_pump_time, 20))
    if soil >= 75: calc_pump_time = 0

    # 5️⃣ PUMP CONTROL LOGIC
    new_pump_on = current_pump_on
    if current_pump_on and time.time() >= pump_stop_time:
        new_pump_on = False
        print("🛑 Pump Timer Finished")

    if data is not None:
        if soil < 65 and not current_pump_on:
            new_pump_on = True
            pump_stop_time = time.time() + calc_pump_time
            print(f"🌵 Soil Dry - Starting Pump for {calc_pump_time:.1f}s")
        elif soil > 75 and current_pump_on:
            new_pump_on = False
            print("✅ Soil Saturated - Stopping Pump")

    # If pump state changed, force one more sync to update relay immediately
    if new_pump_on != current_pump_on:
        esp_sync(new_threat_active, new_pump_on)
        current_pump_on = new_pump_on

    # Steady Loop
    elapsed = time.time() - loop_start
    time.sleep(max(0.1, 0.5 - elapsed))
