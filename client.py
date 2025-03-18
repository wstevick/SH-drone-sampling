import tkinter as tk
import atexit
import threading
import socket
import tkinter.font as tkfont
from tkinter.simpledialog import askstring
from tkinter.filedialog import askdirectory
import os
from tkinter.messagebox import askyesno, showinfo

import parse_arduino_data

HOST = "192.168.4.1"
PORT = 123
TIMEOUT = 3


class NoConnection(Exception):
    pass


class ControlGUI:
    def __init__(self, master, font):
        # try to establish a connection
        self.master = master
        master.title("Arduino Control")
        master.geometry("")

        self.taking_data = False

        # top panel, with all the buttons
        self.controls = tk.Frame(master)
        self.controls.pack(padx=10, pady=10, fill=tk.X)
        self.buttons = {
            "toggle": tk.Button(
                self.controls, text="Take Data", command=self.toggle
            ),
            "format": tk.Button(
                self.controls, text="Format Flash Memory", command=self.format
            ),
            "save": tk.Button(
                self.controls, text="Save Data", command=self.download
            ),
        }
        for idx, btn in enumerate(self.buttons.values()):
            btn.config(font=font, state=tk.DISABLED)
            btn.grid(row=0, column=idx, padx=5, pady=5)

        # bottom panel, with the status display
        self.display = tk.Label(self.master, font=font, justify="left")
        self.display.pack(padx=10, pady=10, fill=tk.BOTH)

        self.socket = None
        self.connect_to_arduino()

        self.update_status_loop()

    def connect_to_arduino(self):
        # real work happens in another thread, to avoid blocking mainloop
        threading.Thread(target=self._connect_to_arduiono, daemon=True).start()

    def _connect_to_arduiono(self):
        """Form a socket connection with the arduino"""
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((HOST, PORT))
                break
            except OSError:
                continue
        s.settimeout(TIMEOUT)
        # all the work done on a seperate variable that's then moved to self.socket
        # that way, the main thread won't try to do anything to it while we're still getting it ready
        self.socket = s
        atexit.register(s.close)
        self.update_status()

    def update_status_loop(self):
        """Update the status twice a second"""
        # run every half second
        self.master.after(500, self.update_status_loop)
        self.update_status()

    def update_status(self):
        try:
            # ask for an update
            self.send("U")
            # process the update using seperate module
            (
                self.taking_data,
                corrupted_files,
                [
                    _,
                    temp,
                    humidity,
                    timestamp,
                    lat,
                    lon,
                    altitude,
                    fixtype,
                    satellites,
                ],
                savedfiles,
            ) = parse_arduino_data.parseupdate(self.getline)
        except NoConnection:
            return

        # update the buttons statuses
        for name, btn in self.buttons.items():
            if name == "toggle":
                btn.config(
                    state=tk.NORMAL,
                    text=(
                        "Stop Taking Data" if self.taking_data else "Take Data"
                    ),
                )
            elif name == "format":
                btn.config(
                    state=tk.DISABLED if self.taking_data else tk.NORMAL
                )
            elif name == "save":
                btn.config(state=tk.NORMAL)

        # set the display
        # example:
        #
        # Taking Data
        # 8:06:55 EST
        # 23C at 28% humidity
        # Location 130,800, altitude 138.3
        # Fix type: GPS (8 satellites)
        #
        # Saved files:
        # save-2025-03-09 - 3 minutes, 4 seconds of data
        # testfile - 1 minute, 38 seconds of data
        # 1 file(s) corrupted
        lines = [
            "Taking Data" if self.taking_data else "Not Taking Data",
            "",
            timestamp,
            f"{temp}C at {humidity}% humidity",
            f"Location {lat},{lon}, altitude {altitude}",
            f"Fix type: {fixtype} ({satellites} satellites)",
        ]
        if savedfiles:
            lines.extend(["", "Saved files:"])
            for filename, savedtime in savedfiles.items():
                minutes, seconds = divmod(savedtime, 60)
                hours, minutes = divmod(minutes, 60)
                lines.append(f"{filename} - {hours}:{minutes}:{seconds}")
        if corrupted_files:
            lines.append(f"{corrupted_files} file(s) corrupted")
        self.display.config(text="\n".join(lines))

    def getline(self):
        """Get one line from the arduino"""
        if self.socket is None:
            raise NoConnection

        line = bytearray()

        try:
            with open(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "log"
                ),
                "ab",
            ) as f:
                while True:
                    char = self.socket.recv(1)
                    f.write(char)
                    if char == b"":
                        raise TimeoutError
                    if char == b"\n":
                        break
                    if char == b"\r":
                        continue
                    line.extend(char)
        except OSError:
            self.handle_disconnect()
            raise NoConnection

        return line.decode()

    def send(self, message):
        """Send a message to the arduino"""
        if self.socket is None:
            raise NoConnection

        message_bytes = message.encode()
        try:
            sent = self.socket.send(message_bytes)
        except TimeoutError:
            sent = -1

        if sent != len(message_bytes):
            self.handle_disconnect()
            raise NoConnection

    def handle_disconnect(self):
        """Disable all buttons, clear the display, and try to reconnect to the arduino"""
        for btn in self.buttons.values():
            btn.config(state=tk.DISABLED)
        self.display.config(text="")

        self.socket.close()
        self.socket = None

        self.connect_to_arduino()

    def toggle(self):
        try:
            if self.taking_data:
                self.send("S")
                self.buttons["toggle"].config(text="Take Data")
            else:
                fname = askstring("File Name", "Enter name of save file")
                if fname:
                    self.send(f"T{fname.strip()}\n")
                    self.buttons["toggle"].config(text="Stop Taking Data")
        except NoConnection:
            pass

    def format(self):
        if askyesno("Format?", "Are you sure you want to format everything?"):
            try:
                self.send("F")
            except NoConnection:
                pass

    def download(self):
        save_dir = askdirectory()
        if save_dir:
            self.send("P")
            saved_files = parse_arduino_data.save_data_to(
                save_dir, self.getline
            )
            showinfo(message=f"{saved_files} downloaded")


def main():
    root = tk.Tk()
    font = tkfont.Font(size=20)
    gui = ControlGUI(root, font)
    root.mainloop()


if __name__ == "__main__":
    main()
