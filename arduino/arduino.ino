#include <ESP8266WiFi.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>

// ---------------- PIN CONFIG ----------------
#define DHTPIN D4
#define DHTTYPE DHT22
#define SOIL_PIN A0
#define RELAY_PIN D5
#define BUZZER_PIN D6  // ← NEW: Buzzer Pin

#define SOIL_DRY_VALUE 1024
#define SOIL_WET_VALUE 400

// ---------------- OLED ----------------
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SH1106G display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ---------------- OBJECTS ----------------
DHT dht(DHTPIN, DHTTYPE);
WiFiServer server(80);

// ---------------- GLOBAL STATE ----------------
String systemState = "IDLE";
bool pumpStatus = false;
String aiReasoning = "অপেক্ষা করা হচ্ছে..."; // LLM Explanation in Bangla

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // Relay OFF (Active Low)

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW); // Buzzer OFF

  Wire.begin(D2, D1);
  if (!display.begin(0x3C, true)) Serial.println("OLED not found!");

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(0, 0);
  display.println("AgriSentinel");
  display.println("Connecting WiFi...");
  display.display();

  const char* ssid = "Zoom";
  const char* password = "majargate";
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  server.begin();
}

// ---------------- LOOP ----------------
void loop() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  int soil_raw = analogRead(SOIL_PIN);
  int soil = constrain(map(soil_raw, SOIL_DRY_VALUE, SOIL_WET_VALUE, 0, 100), 0, 100);

  if (isnan(temp) || isnan(hum)) { temp = 0; hum = 0; }

  // Buzzer Control (Only on Threat)
  if (systemState == "THREAT!") {
    digitalWrite(BUZZER_PIN, HIGH);
  } else {
    digitalWrite(BUZZER_PIN, LOW);
  }

  // OLED Display
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("AgriSentinel v2");
  display.setCursor(0, 10);
  display.print("Temp: "); display.print(temp); display.println(" C");
  display.print("Hum:  "); display.print(hum); display.println(" %");
  display.print("Soil: "); display.println(soil);
  display.setCursor(0, 40);
  display.print("S: "); display.print(systemState);
  display.print(" | P: "); display.println(pumpStatus ? "ON" : "OFF");
  display.setCursor(0, 54); 
  display.print("IP: "); display.print(WiFi.localIP());
  display.display();

  WiFiClient client = server.available();
  if (client) {
    String request = client.readStringUntil('\r');
    client.flush();

    // 1. UPDATE AI REASONING (From Python)
    if (request.indexOf("msg=") != -1) {
        int startPos = request.indexOf("msg=") + 4;
        int endPos = request.indexOf(" HTTP");
        if (endPos == -1) endPos = request.length();
        aiReasoning = urlDecode(request.substring(startPos, endPos));
    }

    if (request.indexOf("/sync") != -1) {
        // Sync State (Threat & Pump)
        if (request.indexOf("t=1") != -1) systemState = "THREAT!";
        else if (request.indexOf("t=0") != -1) systemState = "IDLE";

        if (request.indexOf("p=1") != -1) { digitalWrite(RELAY_PIN, LOW); pumpStatus = true; }
        else if (request.indexOf("p=0") != -1) { digitalWrite(RELAY_PIN, HIGH); pumpStatus = false; }
    }

    // --- 2. RESPOND ---
    if (request.indexOf("GET /dashboard") != -1) {
      // HTML Dashboard Response
      client.println("HTTP/1.1 200 OK");
      client.println("Content-Type: text/html; charset=utf-8");
      client.println("");
      client.println("<!DOCTYPE HTML><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>");
      client.println("<style>body{font-family:Arial; text-align:center; background:#f4f4f4; margin:0; padding:20px;}");
      client.println(".card{background:white; padding:20px; border-radius:15px; box-shadow:0 4px 8px rgba(0,0,0,0.1); margin:10px auto; max-width:400px;}");
      client.println("h1{color:#2c3e50;} .status{font-weight:bold; font-size:1.2em;}");
      client.println(".threat{color:red;} .safe{color:green;} .pump-on{color:blue;} .pump-off{color:gray;}");
      client.println(".ai-box{background:#e8f4fd; border-left:5px solid #3498db; padding:15px; margin-top:20px; text-align:left; font-style:italic;}");
      client.println("</style><script>setInterval(function(){location.reload();}, 3000);</script></head><body>");
      client.println("<h1>AgriSentinel Dashboard</h1><p>Live Monitoring System</p>");
      client.print("<div class='card'><h2>Sensors</h2><p>Temp: <b>"); client.print(temp); client.print(" °C</b></p>");
      client.print("<p>Hum: <b>"); client.print(hum); client.print(" %</b></p>");
      client.print("<p>Soil: <b>"); client.print(soil); client.println(" %</b></p></div>");
      client.print("<div class='card'><h2>Status</h2><p>Security: <span class='status ");
      client.print((systemState=="THREAT!")?"threat'>THREAT DETECTED":"safe'>ALL SAFE");
      client.println("</span></p><p>Pump: <span class='status ");
      client.print(pumpStatus?"pump-on'>RUNNING":"pump-off'>STOPPED");
      client.println("</span></p></div>");
      client.print("<div class='card'><h2>🤖 AI Reasoning (Bangla)</h2><div class='ai-box'>"); 
      client.print(aiReasoning); client.println("</div></div></body></html>");
    } 
    else {
      // JSON Response (Combined for Data & Sync)
      String json = "{\"temperature\":" + String(temp) + ",\"humidity\":" + String(hum) + ",\"soil\":" + String(soil) + ",\"pump\":" + String(pumpStatus?1:0) + "}";
      client.println("HTTP/1.1 200 OK");
      client.println("Content-Type: application/json");
      client.print("Content-Length: "); client.println(json.length());
      client.println("Connection: close");
      client.println("");
      client.print(json);
    }
    client.stop();
  }
}

// Helper to decode URL characters (for Bangla support)
String urlDecode(String str) {
    String res = "";
    for (int i = 0; i < str.length(); i++) {
        if (str[i] == '%' && i + 2 < str.length()) {
            String hex = str.substring(i + 1, i + 3);
            res += (char) strtol(hex.c_str(), NULL, 16);
            i += 2;
        } else if (str[i] == '+') {
            res += ' ';
        } else {
            res += str[i];
        }
    }
    return res;
}