#include <Arduino.h>
#include <Wifi.h>
#include <Wire.h>

#include "secrets.h"
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>

// #define NODE_1
// #define NODE_2

void messageHandler(String &topic, String &payload);

char topic_temp[] = "esp32/temperature";
char topic_hum[] = "esp32/humidity";
char topic_light[] = "esp32/light";
char topic_pressure[] = "esp32/pressure";
char topic_test[] = "esp32/test";

#define PUBLISH_INTERVAL 4000

WiFiClientSecure net = WiFiClientSecure();
MQTTClient client = MQTTClient(256);

unsigned long lastPublishTime = 0;

void printMessage(const char *topic, const char *messageBuffer) {
	Serial.println("sent:");
	Serial.print("- topic: ");
	Serial.println(topic);
	Serial.print("- payload:");
	Serial.println(messageBuffer);
}

void sendToAWS(const char *topic, float value) {
  StaticJsonDocument<200> message;
  message["message"] =	value; // Or you can read data from other sensors
  char messageBuffer[512];
  serializeJson(message, messageBuffer);  // print to client

  client.publish(topic, messageBuffer);

  printMessage(topic, messageBuffer);
}

void connectToAWS(char *topics[], int topicsCount) {
  // Configure WiFiClientSecure to use the AWS IoT device credentials
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  // Connect to the MQTT broker on the AWS endpoint we defined earlier
  client.begin(AWS_IOT_ENDPOINT, 8883, net);

  // Create a handler for incoming messages
  client.onMessage(messageHandler);

  Serial.print("ESP32 connecting to AWS IOT");

  while (!client.connect(THINGNAME)) {
    Serial.print(".");
    delay(100);
  }
  Serial.println();

  if (!client.connected()) {
    Serial.println("ESP32 - AWS IoT Timeout!");
    return;
  }

  for (int i = 0; i < topicsCount; i++)
	client.subscribe(topics[i]);

  Serial.println("ESP32  - AWS IoT Connected!");
}

#ifdef NODE_1

#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#define SEALEVELPRESSURE_HPA (1013.25)

Adafruit_BME280 bme; // I2C

unsigned long delayTime;

void messageHandler(String &topic, String &payload) {
  Serial.println("received:");
  Serial.println("- topic: " + topic);
  Serial.println("- payload:");
  Serial.println(payload);
}

void setup() {
	Serial.begin(9600);
	Serial.println(F("BME280 test"));

	bool status;

	status = bme.begin(0x76);  
	if (!status) {
		Serial.println("Could not find a valid BME280 sensor, check wiring!");
		while (1);
	}

	Serial.println("-- Default Test --");
	delayTime = 1000;

	Serial.println();

	WiFi.mode(WIFI_STA);
	WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

	Serial.println("ESP32 connecting to Wi-Fi");

	while (WiFi.status() != WL_CONNECTED) {
		delay(500);
		Serial.print(".");
	}
	Serial.println();

	char *topicsub[] = {topic_light, topic_temp, topic_test};

	connectToAWS(topicsub, 3);
}


void loop() { 
	client.loop();

	if (millis() - lastPublishTime > PUBLISH_INTERVAL) {
		sendToAWS(topic_temp, bme.readTemperature());
		sendToAWS(topic_hum, bme.readHumidity());
		sendToAWS(topic_pressure, bme.readPressure() / 100.0F);

		lastPublishTime = millis();
	}
}

#endif


#ifdef NODE_2

#include <BH1750.h>

#define RELAY_PIN 5

BH1750 lightMeter;

bool relayState = false;

void messageHandler(String &topic, String &payload) {
	Serial.println("received:");
	Serial.println("- topic: " + topic);
	Serial.println("- payload:");
	Serial.println(payload);

	if (topic == topic_test) {
		Serial.println("Received test message");
		relayState = !relayState;

		if (relayState) {
			digitalWrite(RELAY_PIN, HIGH);
		} else {
			digitalWrite(RELAY_PIN, LOW);
		}
	}
}

void setup() {
	Serial.begin(9600);

	// Initialize the I2C bus (BH1750 library doesn't do this automatically)
	Wire.begin();
	// On esp8266 you can select SCL and SDA pins using Wire.begin(D4, D3);
	// For Wemos / Lolin D1 Mini Pro and the Ambient Light shield use Wire.begin(D2, D1);

	lightMeter.begin();

	Serial.println(F("BH1750 Test begin"));

	pinMode(RELAY_PIN, OUTPUT);  

	WiFi.mode(WIFI_STA);
	WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

	Serial.println("ESP32 connecting to Wi-Fi");

	while (WiFi.status() != WL_CONNECTED) {
		delay(500);
		Serial.print(".");
	}
	Serial.println();

	char *topicsub[] = {topic_hum, topic_pressure, topic_test};

	connectToAWS(topicsub, 3);
}

void loop() {
	client.loop();

	if (millis() - lastPublishTime > PUBLISH_INTERVAL) {
		sendToAWS(topic_light, lightMeter.readLightLevel());
		lastPublishTime = millis();
	}
}
#endif
