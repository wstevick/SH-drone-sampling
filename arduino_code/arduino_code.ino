#include <DHT.h>
#include <LittleFS.h>
#include <ESP8266WiFi.h>
#include <Adafruit_GPS.h>

// setup for the LED
#define LEDPIN 16  // builtin led
bool lastState;
void setState(bool state) {
  if (state != lastState)
    digitalWrite(LEDPIN, state ? LOW : HIGH);
  lastState = state;
}

// DHT things
#define DHTPIN 14  // D5
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

// measurement things
bool takingData = false;
unsigned long startedTakingData;
unsigned long nextObservationTime;
#define SECONDS_PER_OBSERVATION 3

// wifi things
WiFiServer server(123);
WiFiClient client;
bool hasClient = false;

// GPS things
Adafruit_GPS GPS(&Serial);

// save file things
File savefile;
#define DATA_DIR "/"
struct Observation {
  unsigned long sinceStart;  // time since we started taking data, milliseconds

  // climate data
  float temp;      // C
  float humidity;  // %

  // timestamp (GMT)
  uint8_t hour;
  uint8_t minute;
  uint8_t seconds;

  // location data
  nmea_float_t latitude;   // format DDMM.MMMM
  char lat;                // N or S
  nmea_float_t longitude;  // format DDDMM.MMMM
  char lon;                // E or W
  nmea_float_t altitude;   // centimeters

  // GPS diagnostic data;
  uint8_t fixquality;   // 0 = no fix, 1 = GPS, 2 = DGPS
  uint8_t nsatellites;  // number of satellites
};
struct Observation latestObs;

// print message to the Serial, then panic flash the LED so they know something's wrong
void makeError(String message) {
  Serial.begin(9600);
  Serial.println();
  Serial.println(message);
  while (true) {
    setState(!lastState);
    delay(300);
  }
}

void setup() {
  // configure the pin for the LED we use to communicate to the user
  pinMode(LEDPIN, OUTPUT);
  lastState = true;
  setState(false);

  // try to start the WiFi access point
  // if we fail, stop everything and panic blink the LED
  if (!WiFi.softAP("Sampling WiFi", "very secret")) makeError("Couldn't start WiFi");

  // try to mount the flash filesystem
  // if we fail, stop everything and panic blink the LED
  if (!LittleFS.begin()) makeError("Couldn't mount FS");

  server.begin();

  // let power stabilize, then enable DHT
  delay(1000);
  dht.begin();
  nextObservationTime = millis() + SECONDS_PER_OBSERVATION * 1000;

  // GPS setup commands
  GPS.begin(9600);
  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);  // select the data we receive
  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);     // 1 update/sec

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
    if (order == 'T') {  // Take data
      if (takingData) {
        // if we're already getting data, ignore the file name they tried to send
        client.readStringUntil('\n');
      } else {
        startedTakingData = millis();
        String fname = client.readStringUntil('\n');
        fname.trim();
        // do nothing if they don't send a file name
        if (fname.length()) {
          savefile = LittleFS.open(DATA_DIR + fname, "w");
          takingData = true;
        }
      }
    } else if (order == 'S' && takingData) {  // Stop taking data
      savefile.close();
      takingData = false;
    } else if (order == 'P') {  // Print data
      Dir dataDir = LittleFS.openDir(DATA_DIR);
      while (dataDir.next()) {
        if (dataDir.fileSize() % sizeof(Observation) == 0) {
          client.println(dataDir.fileName());

          struct Observation loadObs;
          File readfile = dataDir.openFile("r");
          while (readfile.available() >= sizeof(loadObs)) {
            readfile.readBytes((char*)&loadObs, sizeof(loadObs));
            printObservation(loadObs);
          }
        }

        client.println();
      }
      client.println();
    } else if (order == 'F' && !takingData) {  // Format flash memory
      LittleFS.format();
    } else if (order == 'U') {  // send status Update
      sendStatusUpdate();
    }
  }

  // update GPS information
  while (GPS.available()) {
    GPS.read();
    if (GPS.newNMEAreceived() && GPS.parse(GPS.lastNMEA())) {
      latestObs.hour = GPS.hour;
      latestObs.minute = GPS.minute;
      latestObs.seconds = GPS.seconds;

      latestObs.latitude = GPS.latitude;
      latestObs.lat = GPS.lat;
      latestObs.longitude = GPS.longitude;
      latestObs.lon = GPS.lon;
      latestObs.altitude = GPS.altitude;

      latestObs.fixquality = GPS.fixquality;
      latestObs.nsatellites = GPS.satellites;
    }
  }

  // if we're taking data, and the time has come for the next observation
  unsigned long now = millis();
  if (now > nextObservationTime) {
    while (now > nextObservationTime)
      nextObservationTime += SECONDS_PER_OBSERVATION * 1000;

    latestObs.sinceStart = now - startedTakingData;
    latestObs.temp = dht.readTemperature();
    latestObs.humidity = dht.readHumidity();

    if (isnan(latestObs.temp) || isnan(latestObs.humidity)) {
      // give an annoyed blink if we can't read DHT
      for (int i = 0; i < 6; i++) {
        setState(!lastState);
        delay(50);
      }
    }
    if (takingData) {
      savefile.write((char*)&latestObs, sizeof(latestObs));
      savefile.flush();
    }
  }

  if (!takingData && !hasClient) {  // on startup, no client, two fast blinks per second
    unsigned long throughSecond = millis() % 1000;
    setState(throughSecond < 100 || 200 < throughSecond && throughSecond < 300);
  } else if (!takingData && hasClient) {  // once we get a client, blink on and off twice/second
    setState(millis() % 1000 < 500);
  } else if (takingData && hasClient) {  // if we start taking data, hold on and blink off once per second
    setState(millis() % 1000 > 200);
  } else if (takingData && !hasClient) setState(true);  // if they disconnect, hold on
}

// send an Observation to the client, as CSV
void printObservation(struct Observation obs) {
  client.printf("%d,%f,%f,%d:%d:%d (GMT),%f%c,%f%c,%f,%d,%d\n",
                obs.sinceStart,
                obs.temp, obs.humidity,
                obs.hour, obs.minute, obs.seconds,
                obs.latitude, obs.lat, obs.longitude, obs.lon, obs.altitude,
                obs.fixquality, obs.nsatellites);
}

// send the current sensor readings, the amount of data saved, the files, and the board status
void sendStatusUpdate() {
  // print latest observation
  printObservation(latestObs);
  // print the time saved in each file
  unsigned corruptedFiles = 0;
  Dir dataDir = LittleFS.openDir(DATA_DIR);
  while (dataDir.next()) {
    size_t size = dataDir.fileSize();
    // silently ignore invalid files
    if (size % sizeof(Observation) == 0) {
      client.println(dataDir.fileName());
      client.println(size / sizeof(Observation) * SECONDS_PER_OBSERVATION);
    } else {
      corruptedFiles++;
    }
  }

  client.printf("/%s%d\n", takingData ? "T" : "N", corruptedFiles);
}
