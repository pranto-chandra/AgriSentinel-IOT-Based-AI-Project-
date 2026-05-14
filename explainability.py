import google.generativeai as genai
import os

# -------- GEMINI CONFIGURATION --------
# Replace with your actual API Key
GEMINI_API_KEY = "AIzaSyDYxRXodpjWKRIBy_XOX4dR-daC9rlJf9g"

if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("⚠️ WARNING: Gemini API Key not set in explainability.py. Explainability will be limited.")

genai.configure(api_key=GEMINI_API_KEY)

def get_explanation(soil, temp, hum, pump_time, threat):
    """
    Generates a human-readable explanation of the system's decision.
    """
    if "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY:
        return get_explanation_fallback(soil, temp, hum, pump_time, threat)

    # Construct prompt for Gemini
    prompt = f"""
    You are AgriSentinel, an intelligent agricultural assistant. 
    Explain the following irrigation decision to a farmer in one short, clear sentence in Bengali (Bangla language):
    - Sensor Data: Soil Moisture {soil}%, Temperature {temp}C, Humidity {hum}%.
    - Threat Detected: {'Yes' if threat else 'No'}.
    - Decision: The pump will run for {pump_time:.1f} seconds.
    
    Tell the farmer exactly how many seconds the pump will run and why, based on the soil/weather.
    If a threat was detected, mention it as an urgent security alert. 
    Keep the explanation short, practical, and clear.
    """

    try:
        # Using gemini-flash-latest as identified in your environment
        model_flash = genai.GenerativeModel('models/gemini-flash-latest')
        response = model_flash.generate_content(prompt)
        return response.text.strip()
    except Exception:
        # If API fails, use the beautiful Bangla fallback
        return get_explanation_fallback(soil, temp, hum, pump_time, threat)


def get_explanation_fallback(soil, temp, hum, pump_time, threat):
    reason = f"মাটির আর্দ্রতা={soil}%। "
    if threat:
        reason += "সতর্কতা: জমিতে হুমকি শনাক্ত করা হয়েছে! "
    
    if pump_time > 0:
        reason += f"পাম্প {pump_time:.1f} সেকেন্ডের জন্য চালু করা হয়েছে।"
    else:
        reason += "এই মুহূর্তে সেচের প্রয়োজন নেই।"
    return reason

if __name__ == "__main__":
    # Test
    print(get_explanation(45, 32, 20, 85, False))
    print(get_explanation(45, 32, 20, 0, True))
