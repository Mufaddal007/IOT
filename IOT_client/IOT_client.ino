#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#define led_pin LED_BUILTIN

const char *ssid = "Mufaddal_router";
const char *password = "darbar@777";

const char *server = "http://192.168.31.113:1000";

unsigned long lastPost = 0;
unsigned long lastGet = 0;



void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected");
  pinMode(led_pin, OUTPUT); 
}

void loop() {

  unsigned long now = millis();
  // if(now - lastPost > 5000){
  //   lastPost = now;
  //     sendSensorData();
  // }

  if (now - lastGet > 2000) {
    lastGet = now;
    getState();
  }
}



void sendSensorData() {
  WiFiClient client;
  HTTPClient http;

  http.begin(client, String(server) + "/api/sensor");
  http.addHeader("Content-Type", "application/json");

  String json = "{\"moisture\":45}";

  int code = http.POST(json);

  Serial.println("POST code: " + String(code));
  http.end();
}


void getState() {
  WiFiClient client;
  HTTPClient http;

  http.begin(client, String(server) + "/api/state");

  //http.begin(client, "http://example.com");

  int code = http.GET();
  //int code1 = http.GET(); 

  Serial.println(code); 

  //Serial.println(code1); 
  if (code > 0) {
    String payload = http.getString();
    Serial.println("Raw: " + payload);
    StaticJsonDocument<200> doc; 
    DeserializationError error  = deserializeJson(doc, payload); 

    if(!error){

      const char* led = doc["led"]; 
      const char* pump = doc["pump"]; 

      Serial.println(String("LED: ") + led); 
      Serial.println(String("PUMP: ") + pump); 

      if(strcmp(led, "on")==0){
        Serial.println("making led on");
        digitalWrite(led_pin, LOW); 
      }
      else{
        digitalWrite(led_pin, HIGH); 
      }
    }else{
      Serial.println("Json parsing failed"); 
    }
  }
  http.end();
}
