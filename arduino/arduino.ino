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

// Soil moisture calibration values
// THESE VALUES NEED TO BE CALIBRATED FOR YOUR SENSOR:
// - dry_value: ADC reading when sensor is completely DRY in air
// - wet_value: ADC reading when sensor is completely WET in water
#define SOIL_DRY_VALUE 1024    // ADC value when completely dry
#define SOIL_WET_VALUE 400     // ADC value when in water


// ---------------- OLED ----------------
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SH1106G display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ---------------- OBJECTS ----------------
DHT dht(DHTPIN, DHTTYPE);

// ---------------- WIFI ----------------
// const char* ssid = "Advaita Voice";
// const char* password = "voice1234";

const char* ssid = "Zoom";
const char* password = "majargate";

WiFiServer server(80);

// ---------------- GLOBAL STATE ----------------
String systemState = "IDLE";
bool pumpStatus = false;

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);

  dht.begin();

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // Pump OFF initially

  // OLED init (SDA = D2, SCL = D1)
  Wire.begin(D2, D1);

  if (!display.begin(0x3C, true)) {
    Serial.println("OLED not found!");
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SH110X_WHITE);

  display.setCursor(0, 0);
  display.println("AgriSentinel");
  display.println("Connecting WiFi...");
  display.display();

  // WiFi connect
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.println(WiFi.localIP());

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("WiFi Connected");
  display.println(WiFi.localIP());
  display.display();

  server.begin();
}

// ---------------- LOOP ----------------
void loop() {

  // -------- SENSOR READINGS --------
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  int soil_raw = analogRead(SOIL_PIN);
  
  // Convert soil ADC to percentage (0-100%)
  int soil = constrain(map(soil_raw, SOIL_DRY_VALUE, SOIL_WET_VALUE, 0, 100), 0, 100);

  if (isnan(temp) || isnan(hum)) {
    temp = 0;
    hum = 0;
  }

  // -------- OLED DISPLAY (ALWAYS REFRESH) --------
  /*
  display.clearDisplay();

  display.setCursor(0, 0);
  display.println("AgriSentinel");

  display.setCursor(0, 12);
  display.print("Temp: ");
  display.print(temp);
  display.println(" C");

  display.print("Hum: ");
  display.print(hum);
  display.println(" %");

  display.print("Soil: ");
  display.println(soil);

  display.println("----------------");

  display.print("State: ");
  display.println(systemState);

  display.print("Pump: ");
  display.println(pumpStatus ? "ON" : "OFF");

  display.display();
  */

  display.clearDisplay();
  display.setTextSize(1); // Ensure text is small
  display.setTextColor(SH110X_WHITE);

  // Header
  display.setCursor(0, 0);
  display.println("AgriSentinel");

  // Sensor Data
  display.setCursor(0, 10);
  display.print("Temp: "); 
  display.print(temp); 
  display.println(" C"); // 1 decimal place to save space
  
  display.setCursor(0, 20);
  display.print("Hum:  "); 
  display.print(hum); 
  display.println(" %");

  display.setCursor(0, 30);
  display.print("Soil: "); 
  display.println(soil);

  // System Status
  display.setCursor(0, 40);
  display.print("S: "); display.print(systemState);
  display.print(" | P: "); display.println(pumpStatus ? "ON" : "OFF");

  // IP Address (Static at bottom)
  display.setCursor(0, 54); 
  display.print("IP: ");
  display.print(WiFi.localIP());

  display.display();

  // -------- HANDLE CLIENT REQUEST --------
  WiFiClient client = server.available();

  if (client) {
    // Set timeout for client
    client.setTimeout(5000);
    
    String request = client.readStringUntil('\r');
    Serial.print("Request: ");
    Serial.println(request);
    
    client.flush();

    // -------- CONSOLIDATED SYNC COMMAND --------
    if (request.indexOf("/sync") != -1) {
      // Parse threat state (?t=1 or ?t=0)
      if (request.indexOf("t=1") != -1) {
        systemState = "THREAT!";
      } else if (request.indexOf("t=0") != -1) {
        systemState = "IDLE";
      }

      // Parse pump state (?p=1 or ?p=0)
      if (request.indexOf("p=1") != -1) {
        digitalWrite(RELAY_PIN, LOW); // Active Low: LOW is ON
        pumpStatus = true;
      } else if (request.indexOf("p=0") != -1) {
        digitalWrite(RELAY_PIN, HIGH); // Active Low: HIGH is OFF
        pumpStatus = false;
      }
      Serial.println("Sync complete");
    }

    // -------- INDIVIDUAL COMMANDS (Backwards compatibility) --------
    if (request.indexOf("/pump_on") != -1) {
      digitalWrite(RELAY_PIN, LOW);
      pumpStatus = true;
    }

    if (request.indexOf("/pump_off") != -1) {
      digitalWrite(RELAY_PIN, HIGH);
      pumpStatus = false;
    }

    if (request.indexOf("/threat") != -1) {
      systemState = "THREAT!";
    }

    if (request.indexOf("/idle") != -1) {
      systemState = "IDLE";
    }

    // -------- PREPARE JSON RESPONSE --------
    String jsonResponse = "{";
    jsonResponse += "\"temperature\":"; jsonResponse += temp; jsonResponse += ",";
    jsonResponse += "\"humidity\":"; jsonResponse += hum; jsonResponse += ",";
    jsonResponse += "\"soil\":"; jsonResponse += soil; jsonResponse += ",";
    jsonResponse += "\"pump\":"; jsonResponse += (pumpStatus ? 1 : 0);
    jsonResponse += "}";

    // -------- SEND HTTP RESPONSE WITH PROPER HEADERS --------
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: application/json");
    client.print("Content-Length: ");
    client.println(jsonResponse.length());
    client.println("Connection: close");
    client.println("");
    client.print(jsonResponse);
    client.println();

    // Ensure client disconnects
    client.flush();
    client.stop();
    delay(10);
  }

  // No delay here ensures the server is always listening for commands!
}