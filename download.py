import socket
import os
from parse_arduino_data import save_data_to
import atexit
import functools


def getline(s):
    """Get one line from the arduino"""
    line = bytearray()

    while True:
        char = s.recv(1)
        if char == b"":
            raise TimeoutError
        if char == b"\n":
            break
        if char == b"\r":
            continue
        line.extend(char)

    print(line)
    return line.decode()


def main():
    print("getting connection...", end="", flush=True)
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("192.168.4.1", 123))
            break
        except OSError:
            print(".", end="", flush=True)
            continue

    print("conntected!")
    s.settimeout(5)
    atexit.register(s.close)

    save_dir = input("Where to save data to? ").strip()
    if os.path.exists(save_dir):
        if not os.path.isdir(save_dir):
            print("That's a file!")
            return
    else:
        os.makedirs(save_dir)

    s.sendall(b"P")
    saved_files = save_data_to(save_dir, functools.partial(getline, s))
    print(saved_files, "downloaded")


if __name__ == "__main__":
    main()
