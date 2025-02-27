#include <ESP8266WiFi.h>

WiFiServer server(123);

long int start;

void setup() {
  WiFi.softAP("Sampling WiFi", "very secret");

  server.begin();
}

void loop() {
  WiFiClient client = server.accept();
  if (client) {
    start = millis();
    int rounds = 0;
    while (client.connected()) {
      client.printf("%d\n", millis());
      rounds++;
      delay(1000);
    }
    client.stop();
  }
}