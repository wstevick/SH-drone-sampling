# copied and modified from https://www.geeksforgeeks.org/python-asksaveasfile-function-in-tkinter/#
import socket
from _thread import start_new_thread, allocate_lock
from tkinter import *
from tkinter import ttk

from tkinter.filedialog import asksaveasfile

root = Tk()
root.geometry('200x150')

getting_data_lock = allocate_lock()
getting_data = [False]


def save():
    files = [('CSV documents', '*.csv'),
             ('All Files', '*.*')]
    savefile = asksaveasfile(filetypes=files, defaultextension=files)
    if savefile is not None:
        btn.configure(command=stop, text='Taking Data - Finish')
        start_new_thread(getdata, (savefile,))


def stop():
    with getting_data_lock:
        getting_data[0] = False
    btn.configure(command=save, text='Take Data')


def getdata(savefile):
    getting_data[0] = True
    savefile.write('Humidity,Temperature\n')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('192.168.4.1', 123))
    s.settimeout(5)
    try:
        with s.makefile() as f:
            for line in f:
                with getting_data_lock:
                    if not getting_data[0]:
                        break
                savefile.write(line)
    finally:
        s.close()
        savefile.close()
        stop()


btn = ttk.Button(root, text='Take Data', command=save)
btn.pack(side=TOP, pady=20)

mainloop()
