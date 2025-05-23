#include <LittleFS.h>
#include <Adafruit_GPS.h>
#include <ESP8266WiFi.h>

// what's the name of the hardware serial port?
#define GPSSerial Serial

// Connect to the GPS on the hardware port
Adafruit_GPS GPS(&GPSSerial);

WiFiServer server(123);

void setup() {
  WiFi.softAP("MATH II (GPS logging)", "very secret");
  LittleFS.begin();
  server.begin();
  //while (!Serial);  // uncomment to have the sketch wait until Serial is ready

  // connect at 115200 so we can read the GPS fast enough and echo without dropping chars
  // also spit it out
  GPS.begin(9600);
  // uncomment this line to turn on RMC (recommended minimum) and GGA (fix data) including altitude
  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);  // select the data we receive
  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);     // 1 update/sec

  delay(1000);

  // Ask for firmware version
  GPSSerial.println(PMTK_Q_RELEASE);
}

void loop()  // run over and over again
{
  WiFiClient client = server.accept();
  if (client && client.connected()) {
    File savefile = LittleFS.open("/log", "r");
    while (savefile.available()) client.write(savefile.read());
    savefile.close();
    client.stop();
  }
  GPS.read();
  // if a sentence is received, we can check the checksum, parse it...
  if (GPS.newNMEAreceived()) {
    File savefile = LittleFS.open("/log", "a");
    savefile.print(GPS.lastNMEA());
    savefile.close();
  }
}