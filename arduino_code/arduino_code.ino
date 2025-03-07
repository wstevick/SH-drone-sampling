#include <DHT.h>
#include <LittleFS.h>
#include <ESP8266WiFi.h>

// setup for the LED
#define LEDPIN 16 // D0, builtin led
bool lastState;
void setState(bool state) {
  if (state != lastState)
    digitalWrite(LEDPIN, state ? LOW : HIGH);
  lastState = state;
}

// DHT things
#define DHTPIN 2  // D4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// save file things
struct Observation {
  unsigned long sinceStart;
  float temp;
  float humidity;
};
File savefile;
#define DATA_DIR "/"

// measurement things
bool takingData = false;
unsigned long startedTakingData;
unsigned long nextObservationTime;
#define SECONDS_PER_OBSERVATION 3

// wifi things
WiFiServer server(123);
WiFiClient client;
bool hasClient = false;

void setup() {
  // configure the pin for the LED we use to communicate to the user
  pinMode(LEDPIN, OUTPUT);
  setState(false);

  Serial.begin(9600);
  Serial.println();

  // try to start the WiFi access point
  // if we fail, stop everything and panic blink the LED
  if (!WiFi.softAP("Sampling WiFi", "very secret")) {
    Serial.println("Failed to start WiFi");
    while (true) {
      setState(!lastState);
      delay(300);
    }
  }

  // try to mount the flash filesystem
  // if we fail, stop everything and panic blink the LED
  if (!LittleFS.begin()) {
    Serial.println("Failed to mount FS");
    while (true) {
      setState(!lastState);
      delay(300);
    }
  }

  server.begin();

  // let power stabilize
  delay(1000);
  dht.begin();

  // blink code to show that we've started
  setState(true);
  delay(600);
  setState(false);
  delay(300);
  setState(true);
  delay(600);
  setState(false);
}

void loop() {
  // try to get a WiFi client if we don't have one
  hasClient = client && client.connected();
  if (!hasClient) {
    client = server.accept();

    hasClient = client && client.connected();
  }

  // take orders from the client
  if (hasClient && client.available()) {
    char order = client.read();
    if (order == 'T') { // Take data
      if (takingData) {
        // if we're already getting data, ignore the file name they tried to send
        client.readStringUntil('\n');
      } else {
        startedTakingData = millis();
        nextObservationTime = startedTakingData + SECONDS_PER_OBSERVATION * 1000;
        String fname = client.readStringUntil('\n');
        // do nothing if they don't send a file name
        if (fname.length()) {
          savefile = LittleFS.open(DATA_DIR + fname, "w");
          takingData = true;
        }
      }
    } else if (order == 'S' && takingData) { // Stop taking data
      savefile.close();
      takingData = false;
    } else if (order == 'P') { // Print data
      Dir dataDir = LittleFS.openDir(DATA_DIR);
      while (dataDir.next()) {
        client.println(dataDir.fileName());

        if (dataDir.fileSize() % sizeof(Observation) == 0) {
          struct Observation obs;
          File readfile = dataDir.openFile("r");
          while (readfile.available() >= sizeof(obs)) {
            readfile.readBytes((char*) &obs, sizeof(obs));
            client.printf("%d,%.2f,%.2f\n", obs.sinceStart, obs.temp, obs.humidity);
          }
        }

        client.println();
      }
      client.println("/DONE!");
    } else if (order == 'F' && !takingData) { // Format flash memory
      LittleFS.format();
    } else if (order == 'U') { // send status Update
      sendStatusUpdate();
    } else if (order != '\n') { // newlines ignored
      client.printf("invalid order '%d'\n", order);
    }
  }

  // if we're taking data, and the time has come for the next observation
  if (takingData && millis() > nextObservationTime) {
    nextObservationTime += SECONDS_PER_OBSERVATION * 1000;

    struct Observation obs = {millis() - startedTakingData, dht.readTemperature(), dht.readHumidity()};
    if (isnan(obs.temp) || isnan(obs.humidity)) {
      // give an annoyed blink if we can't read DHT
      for (int i = 0; i < 6; i++) {
        setState(!lastState);
        delay(50);
      }
    } else {
      savefile.write((char*) &obs, sizeof(obs));
      savefile.flush();
    }
  }

  if (!takingData && !hasClient) { // on startup, no client, two fast blinks per second
    unsigned long throughSecond = millis() % 1000;
    setState(throughSecond < 100 || 200 < throughSecond && throughSecond < 300);
  } else if (!takingData && hasClient) { // once we get a client, blink on and off twice/second
    setState(millis() % 1000 < 500);
  } else if (takingData && hasClient) { // if we start taking data, hold on and blink off once per second
    setState(millis() % 1000 > 100);
  } else if (takingData && !hasClient) setState(true); // if they disconnect, hold on
}

// send the amount of data saved, and the board status
void sendStatusUpdate() {
  // find the total size of the data files
  Dir dataDir = LittleFS.openDir(DATA_DIR);
  size_t totalSize = 0;
  while (dataDir.next()) {
    size_t size = dataDir.fileSize();
    // silently ignore invalid files
    if (size % sizeof(Observation) == 0) {
      totalSize += size;
    }
  }

  client.printf("%s%d\n", takingData ? "T" : "N", totalSize / sizeof(Observation) * SECONDS_PER_OBSERVATION);
}
