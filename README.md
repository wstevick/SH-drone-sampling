# SH-drone-sampling
The arduino runs a wifi access point (SSID “Sampling Wifi”, password “very secret”), and a server on that access point at 192.168.4.1:123, that can be accessed by running `netcat 192.168.4.1 123` on a linux terminal. The server accepts the following commands

 - Tfilename to start taking data to the file. For instance, Tdata-03-07-25 to start taking data to a file called data-03-07-25
 - S to stop taking data
 - F to format the flash memory and delete everything
 - P to print the data saved in every file. Format is

	`Name of file 1`

	`Data in file 1`

	`More data in file 1`



	`Name of file 2`

	`Data in file 2`

	`More data in file 2`



	/DONE!

	Data is csv, format is `milliseconds since recording started,temperature,humidity,gpshour,gpsminute,gpssecond,latitude (DDMM.MMMM)X,longitude (DDDMM.MMMM)X,altitude,fixquality,nsatellites`
 - U says to print an update on the data saved. Format is

	`Latest data point (same format as CSV in P)`
	
	`Name of file 1`

	`Seconds of data stored in file 1`

	`Name of file 2`

	`Seconds of data stored in file 2`

	/`status`

	Where status is either T for Taking data or N for Not taking data



It also uses the following blink patterns:
 - If something goes terribly wrong it will blink on and off quickly forever. Look at the serial output for more information
 - When it’s done starting, it will give two blinks to let you know it’s ready
 - When not taking data, and with no client connected, it will give two short blinks per second
 - When not taking data, but with a client connected, it will blink on and off for a half second each
 - When taking data with a client connected, it will hold on blinking off now and again
 - When taking data with no client connected, it will hold on
 - If it tries to read the DHT22 (using D4) and gets nan values, it will flicker quickly
