#include <DHT.h>
#include <ESP8266WiFi.h>

#define DHTPIN 2  // D4

DHT dht(DHTPIN, DHT22);

WiFiServer server(123);

void setup() {
  WiFi.softAP("Sampling WiFi", "very secret");

  server.begin();
  dht.begin();
}

void loop() {
  WiFiClient client = server.accept();
  if (client) {
    while (client.connected()) {
      float humidity = dht.readHumidity();
      float temperature = dht.readTemperature();
      client.print(humidity);
      client.print(",");
      client.println(temperature);
      delay(3000);
    }
    client.stop();
  }
}