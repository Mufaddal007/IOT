#include <ESP8266WiFi.h>
#include <ArduinoWebsockets.h>
#include <ArduinoJson.h>

using namespace websockets;

const char* ssid = "Mufaddal_router";
const char* password = "darbar@777";

WebsocketsClient client;

#define LED_PIN 2

bool isConnected = false; 
unsigned long lastReconnectAttempt = 0; 
unsigned long lastPingTime = 0; 


void connectWebSocket(){
    Serial.println("Connecting to websocket..."); 
    isConnected = client.connect("192.168.31.113", 8765, "/"); 
    if(isConnected){
        Serial.println("WebSocket Connected"); 
    }
    else{
        Serial.println("Websocket connection failed"); 
    }
}



void onMessageCallback(WebsocketsMessage message) {
    Serial.print("📩 From Server: ");
    Serial.println(message.data());

    DynamicJsonDocument doc(256);
    deserializeJson(doc, message.data());

    if (doc["type"] == "command") {
        String action = doc["action"];

        digitalWrite(LED_PIN, action == "on" ? LOW : HIGH);

        // send ACK
        DynamicJsonDocument res(128);
        res["type"] = "status";
        res["device"] = "led";
        res["state"] = action;

        String out;
        serializeJson(res, out);
        client.send(out);
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);

    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi connected");

    client.onMessage(onMessageCallback);

    connectWebSocket(); 
}

void loop() {
    client.poll(); 
    if(!client.available()){
        isConnected= false; 
    }

    if(!isConnected && millis() - lastReconnectAttempt > 5000){
        lastReconnectAttempt = millis(); 
        connectWebSocket(); 
    }

    if(!isConnected && millis() - lastPingTime >30000){
        client.send("ping"); 
        lastPingTime = millis(); 
        Serial.println("ping send"); 
    }

}