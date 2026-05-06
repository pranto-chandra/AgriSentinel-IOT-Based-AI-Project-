import google.generativeai as genai
import os

# -------- GEMINI CONFIGURATION --------
# Replace with your actual API Key
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("⚠️ WARNING: Gemini API Key not set in explainability.py. Explainability will be limited.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def get_explanation(soil, temp, hum, irrigation, threat):
    """
    Generates a human-readable explanation of the system's decision.
    """
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        # Fallback local explanation
        reason = f"Decision based on: Soil={soil}%, Temp={temp}C, Hum={hum}%. "
        if threat:
            reason += "Action: Irrigation stopped due to threat detected."
        elif irrigation > 70:
            reason += f"Action: Heavy irrigation ({irrigation}%) triggered."
        elif irrigation > 40:
            reason += f"Action: Moderate irrigation ({irrigation}%) triggered."
        else:
            reason += "Action: Minimal or no irrigation needed."
        return reason

    # Construct prompt for Gemini
    prompt = f"""
    You are AgriSentinel, an intelligent agricultural assistant. 
    Explain the following irrigation decision to a farmer in one short, clear sentence:
    - Sensor Data: Soil Moisture {soil}%, Temperature {temp}C, Humidity {hum}%.
    - Threat Detected: {'Yes' if threat else 'No'}.
    - Fuzzy Logic Decision: {irrigation}% irrigation level.
    
    If a threat was detected, explain that safety comes first. 
    Otherwise, explain how the soil and weather conditions led to this specific irrigation level.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"System Decision: {irrigation}% irrigation based on current sensor readings. (API Error: {str(e)})"

if __name__ == "__main__":
    # Test
    print(get_explanation(45, 32, 20, 85, False))
    print(get_explanation(45, 32, 20, 0, True))
