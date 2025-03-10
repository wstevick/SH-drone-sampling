import tkinter as tk
import socket
import tkinter.font as tkfont
import tkinter.messagebox as tkmsg

import parse_arduino_data

HOST = "192.168.4.1"
PORT = 123
TIMEOUT = 3


class NoConnection(Exception):
    pass


class ControlGUI:
    def __init__(self, master, font):
        # try to establish a connection
        self.socket = None
        self.connect_to_arduino() 

        self.master = master
        master.title("Arduino Control")
        master.geometry("")

        # top panel, with all the buttons
        self.controls = tk.Frame(master)
        self.controls.pack(padx=10, pady=10, fill=tk.X)
        self.buttons = [
            tk.Button(self.controls, text="Take Data"),
            tk.Button(self.controls, text="Format Flash Memory"),
            tk.Button(self.controls, text="Save Data"),
        ]
        for idx, btn in enumerate(self.buttons):
            btn.config(font=font, status=tk.DISABLED)
            btn.grid(row=0, column=idx, padx=5, pady=5)

        # bottom panel, with the status display
        self.display = tk.Label(self.master, font=font, justify="left")
        self.display.pack(padx=10, pady=10, fill=tk.BOTH)

        self.update_status()

    def connect_to_arduino(self):
        # real work happens in another thread, to avoid blocking mainloop
        threading.Thread(target=self._connect_to_arduiono, daemon=True).start()

    def _connect_to_arduiono(self):
        """Form a socket connection with the arduino"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.settimeout(TIMEOUT)
        # all the work done on a seperate variable that's then moved to self.socket
        # that way, the main thread won't try to do anything to it while we're still getting it ready
        self.socket = s

    def update_status(self):
        """Get a status update from the arduino board"""
        # run every half second
        self.master.after(500, self.update_status) 
        try:
            # ask for an update
            self.send('U')
            # process the update using seperate module
            [_, temp, humidity, timestamp, lat, lon, altitude, fixtype, satellites], savedfiles = arduino_parsing.parseupdate(self.getline)
            # example
            # 8:06:55 EST
            # 23C at 28% humidity
            # Location 130,800, altitude 138.3
            # Fix type: GPS (8 satellites)
            #
            # Saved files:
            # save-2025-03-09			3 minutes, 4 seconds of data
            # testfile		        	1 minute, 38 seconds of data
            lines = [timestamp,
                     f'{temp}C at {humidity}% humidity',
                     f'Location {lat},{lon}, altitude {altitude}'
                     f'Fix type: {fixtype} ({satellites} satellites)',
                     ''
                     'Saved files:']
            self.display.config(text=lines.join('\n'))

    def getline(self):
        """Get one line from the arduino"""
        if self.socket is None: raise NoConnection

        with self.socket.makefile() as f:
            try:
                return f.readline().strip()
            except TimeoutError:
                self.handle_disconnect()
                raise NoConnection

    def send(message):
        """Send a message to the arduino"""
        if self.socket is None: raise NoConnection

        message_bytes = messagebox.encode()
        try:
            sent = self.socket.send(messagebox)
        except TimeoutError:
            sent = -1

        if sent != len(message_bytes):
            self.handle_disconnect()
            raise NoConnection

    def handle_disconnect(self):
        """Disable all buttons, clear the display, and try to reconnect to the arduino"""
        for btn in self.buttons:
            btn.config(status=tk.DISABLED)
        self.display.config(text='')

        self.socket.close()
        self.socket = None

        self.connect_to_arduino()


def main():
    root = tk.Tk()
    font = tkfont.Font(size=20)
    gui = ControlGUI(root, font)
    root.mainloop()


if __name__ == "__main__":
    main()
