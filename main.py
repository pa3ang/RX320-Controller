# PA3ANG  V1.0  July 2026.
# made on RPi3B with 7" TFT geometrics for Tkinter. 
#
# program uses two classes:
# 	rx320.py which is the RX320 communication, calculation and interrogation
#       dxcluster.py which establishes the communication with a dx cluster via telnet
#
# user specifics are stored in teh rx320.ini file
#
import configparser
import serial
import socket
import threading
import sys
import os
import re
import time
import queue
from tkinter import *
from tkinter import ttk
from rx320 import RX320
from dxcluster import DXCluster

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(base_path, "rx320.ini"))

# Initialise Tkinter window
window = Tk()
window.geometry("800x480")
#window.attributes("-fullscreen", True)
window.wm_title(f"Ten-Tec RX320 Controller. Version 2.0 / RPi layout.")

# Global variables
tune_step=1000
current_mode = StringVar()
current_mode.set("LSB")
current_filter = IntVar()
current_band = StringVar()
current_band.set("40m")
smeter_var = StringVar()
smeter_var.set("S0")

DEFAULT_FILTER = {
    "CW": 600,
    "LSB": 3000,
    "USB": 3000,
    "AM": 8000,
}

current_filter.set(DEFAULT_FILTER["LSB"])

current_agc = StringVar()
current_agc.set("MEDIUM")

# Mode Mapping
RX_MODE = {
    "AM": RX320.MODE_AM,
    "USB": RX320.MODE_USB,
    "LSB": RX320.MODE_LSB,
    "CW": RX320.MODE_CW,
}

FILTERS = {
    8000:33,
    4500:5,
    3000:10,
    2700:12,
    2400:14,
    600:27,
    300:32
}

AGC_MODES = {
    "SLOW": RX320.AGC_SLOW,
    "MEDIUM": RX320.AGC_MEDIUM,
    "FAST": RX320.AGC_FAST,
}

MEMORY_AGC = {
    "CW": "FAST",
    "LSB": "MEDIUM",
    "USB": "MEDIUM",
    "AM": "SLOW",
}

RX_BAND = {
    "160m": 1850000,
    "80m": 3690000,
    "60m": 5354000,
    "40m": 7100000,
    "30m": 10118000,
    "20m": 14200000,
    "17m": 18125000,
    "15m": 21250000,
    "12m": 24915000,
    "10m": 28500000
}

BANDPLAN = []
for start, value in config["Bandplan"].items():
    end, mode = value.split(",")
    BANDPLAN.append(
        (
            int(start),
            int(end),
            mode.strip().upper()
        )
    )

# Initialize RX320
current_frequency = config["Radio"].getint("start_frequency")
current_volume = config["Radio"].getint("volume")

radio = RX320(
    config["Radio"].get("port"),
    freq_offset=config["Radio"].getint("freq_offset"),
    cw_pitch=config["Radio"].getint("cw_pitch")
)

# Initialize DX Cluster
DX_HOST = config["DXCluster"].get("host")
DX_PORT = config["DXCluster"].getint("port")
DX_CALL = config["DXCluster"].get("call")

DX_FILTERS = [
    x.strip()
    for x in config["Filters"]["commands"].splitlines()
    if x.strip()
]

dx_queue = queue.Queue()

radio.set_mode(RX320.MODE_LSB)
radio.set_filter(FILTERS[current_filter.get()])
radio.set_volume(current_volume)
radio.set_agc(RX320.AGC_MEDIUM)
radio.set_freq(current_frequency)

# Funtions 
def load_memories(name):
    memories = []

    for item in config['Memories'][name].split(';'):
        freq, mode = item.split(',')
        memories.append((int(freq), mode))

    return memories

def set_direct_frequency():
    """ Read frequency from panel, convert, check and send to RX320. """
    try:
        freq_khz = float(entry_frequency.get())
        freq_hz = int(freq_khz * 1000)

        if 100000 <= freq_hz <= 30000000:
            set_frequency(freq_hz)

            # display netjes terugzetten
            entry_frequency.delete(0, END)
            entry_frequency.insert(0, f"{current_frequency/1000:.2f}")

        else:
            print("Fout: Frequentie buiten bereik.")

    except ValueError:
        print("Fout: Ongeldige invoer, voer een geldig getal in.")

    finally:
        window.focus()

def set_volume(level):
    global current_volume
    rx_volume = 63 - level
    current_volume = level
    radio.set_volume(rx_volume)
    
def step_frequency(frequency):
    set_frequency(frequency)
      
def set_frequency(frequency):
    global current_frequency
    current_frequency = frequency
    radio.set_freq(frequency)
    # update band display
    for band, freq in RX_BAND.items():
        if abs(freq - frequency) < 500000:
            current_band.set(band)
            break
    window.focus() 
    
def set_mode(mode):
    current_mode.set(mode)
    radio.set_mode(RX_MODE[mode])
    set_frequency(current_frequency)
    
def set_band(band):
    global current_frequency
    current_band.set(band)
    frequency = RX_BAND[band]
    set_frequency(frequency)
    # mode bepalen via bandplan
    mode = bandplan_lookup(frequency)
    if mode:
        set_mode(mode)
        
def set_memory(frequency, mode):
    current_mode.set(mode)
    radio.set_mode(RX_MODE[mode])

    # memory default AGC
    agc = MEMORY_AGC[mode]
    current_agc.set(agc)
    radio.set_agc(AGC_MODES[agc])

    # memory default filter
    filt = DEFAULT_FILTER[mode]
    current_filter.set(filt)
    radio.set_filter(FILTERS[filt])
    set_frequency(frequency)

def set_filter(value):
    value = int(value)
    radio.set_filter(FILTERS[value])
    current_filter.set(value)
    set_mode(radio.get_mode())

def set_agc(value):
    current_agc.set(value)
    radio.set_agc(AGC_MODES[value])
    radio.set_freq(current_frequency)
           
def update_status():
    if window.focus_get() != entry_frequency:
        entry_frequency.delete(0, END)
        entry_frequency.insert(0, f"{current_frequency/1000:.2f}")

    #current_mode.set(radio.get_mode())

    volume_slider.set(current_volume)
    window.after(500, update_status)
    
def update_smeter():
    try:
        level = radio.get_smeter()
    except:
        level = 0

    smeter_canvas.delete("all")

    bw, bh, sp = 15, 18, 3
    total = 11 * (bw + sp) - sp
    start_x = (int(smeter_canvas["width"]) - total) // 2
    scale_y = 30

    # blokjes
    for i in range(11):
        x = start_x + i * (bw + sp)

        if i < 3:
            color = "orange"
        elif i < 9:
            color = "green"
        else:
            color = "red"

        if i >= level:
            color = "#202020"

        smeter_canvas.create_rectangle(x, 3, x + bw, 3 + bh, fill=color, outline="")

    # schaal
    smeter_canvas.create_line(start_x, scale_y, start_x + total, scale_y, fill="white")

    for pos, text in {0:"S0", 2:"S3", 4:"S5", 6:"S7", 8:"S9", 10:"S9+20"}.items():
        x = start_x + pos * (bw + sp) + bw / 2
        smeter_canvas.create_line(x, scale_y-4, x, scale_y+4, fill="white")
        smeter_canvas.create_text(x, 43, text=text, fill="white", font=("Consolas", 8))

    window.after(200, update_smeter)
    
def create_memory_menu(memories, title, column):
    values = [f"{freq//1000:>6} | {mode:<3}" for freq, mode in memories]
    var = StringVar()
    var.set(title)

    def handler(selection):
        mapping = {
            f"{freq//1000:>6} | {mode:<3}":
            (freq, mode)
            for freq, mode in memories
        }

        freq, mode = mapping[selection]
        set_memory(freq, mode)
        # keep literal
        var.set(title)

    menu = OptionMenu(window, var, *values, command=handler)
    menu.config(width=17, bg="orange", font=("Consolas", 10))
    menu["menu"].config(bg="lightgrey", font=("Consolas", 10))
    menu.grid(row=0, column=column, columnspan=2, padx=(42, 2) if column == 0 else (0, 2), pady=2)
    return var

def bandplan_lookup(freq):
    for start, end, mode in BANDPLAN:
        if start <= freq <= end:
            return mode
    return None

def start_dxcluster():
    global cluster
    cluster = DXCluster(
        DX_HOST,
        DX_PORT,
        call=DX_CALL,
        filters=DX_FILTERS,
        callback=dx_spot_received
    )
    threading.Thread(
        target=cluster.connect,
        daemon=True
    ).start()

def dx_double_click(event):
    selection = dx_list.curselection()
    if not selection:
        return
    index = selection[0]
    freq = dx_list.freq.get(index)
    if not freq:
        return
    mode = bandplan_lookup(freq)
    if mode is not None:
        set_memory(freq, mode)

def update_dx_window():
    while not dx_queue.empty():
        display, freq = dx_queue.get()
        dx_list.insert(
            END,
            display
        )
        # frequentie bewaren bij de regel
        dx_list.freq = getattr(dx_list, "freq", {})
        dx_list.freq[dx_list.size()-1] = freq
        dx_list.see(END)
    window.after(200, update_dx_window)

def dx_spot_received(line):
    if not line.startswith("DX de"):
        return
    # FT8/FT4 spots overslaan
    upper = line.upper()
    if "FT8" in upper or "FT4" in upper:
        return
    freq = parse_dx_spot(line)
    if not freq:
        return
    # only frequency allowed within .ini bandplan
    mode = bandplan_lookup(freq)
    if mode is None:
        return
    
    # DX de prefix verwijderen
    display = line.replace("DX de ", " ", 1)
    display = display.replace(":", "", 1)
    dx_queue.put((display, freq))

def parse_dx_spot(line):
    # frequentie zoeken in kHz (bijv. 14252.0)
    match = re.search(r'\s(\d+\.\d+)\s', line)
    if not match:
        return None
    freq_khz = float(match.group(1))

    # alleen 100 kHz t/m 30 MHz
    if freq_khz < 100 or freq_khz > 30000:
        return None
    freq_hz = int(freq_khz * 1000)
    return freq_hz

FIXED_MEMORIES = load_memories("fixed")
EXTRA_1_MEMORIES = load_memories("extra_1")
EXTRA_2_MEMORIES = load_memories("extra_2")

# Create compact screen based on Python Tkinter / Windows
# Input for direct frequency
entry_frequency = Entry(window, width=12, font=('Arial', 30), justify='center', bg='yellow', fg='red')
entry_frequency.grid(column=0, row=1, padx=(42,5), columnspan=2, pady=2)

# huidige frequentie tonen
entry_frequency.insert(0, f"{current_frequency/1000:.2f}")
entry_frequency.bind("<Return>", lambda event: set_direct_frequency())

# Band drop-down menu
band_menu = OptionMenu(window, current_band, *RX_BAND.keys(), command=set_band)
band_menu.config(bg="lightblue", width=6)
band_menu["menu"].config(bg="lightgrey")
band_menu.grid(column= 2, row=1, pady=2, padx=2)

# Mode drop-down menu
mode_menu = OptionMenu(window, current_mode, *RX_MODE.keys(), command=set_mode)
mode_menu.config(bg="lightblue", width=6)
mode_menu["menu"].config(bg="lightgrey")
mode_menu.grid(column=3, row=1, pady=2, padx=2)

# Filter drop-down menu
filter_menu = OptionMenu(window, current_filter, *FILTERS.keys(), command=set_filter)
filter_menu.config(bg="lightblue", width=6)
filter_menu["menu"].config(bg="lightgrey")
filter_menu.grid(column=4, row=1, pady=2, padx=2)

# AGC drop-down menu
agc_menu = OptionMenu(window, current_agc, *AGC_MODES.keys(), command=set_agc)
agc_menu.config(bg="lightblue", width=6)
agc_menu["menu"].config(bg="lightgrey")
agc_menu.grid(column=5, row=1, pady=2, padx=2)

# Frequency 1kHz tuning buttons
button_step_down = Button(window, text="- 1/.1 kHz", bg="lightblue", command=lambda: step_frequency(current_frequency - tune_step), width=10)
button_step_down.grid(column=0, row=2, pady=2, padx=(42, 2))
button_step_up = Button(window, text="+ 1/.1 kHz", bg="lightblue", command=lambda: step_frequency(current_frequency + tune_step), width=10)
button_step_up.grid(column=1, row=2, pady=2, padx=(2, 2))

button_step_down.bind("<Button-3>", lambda e: step_frequency(current_frequency - 100))
button_step_up.bind("<Button-3>", lambda e: step_frequency(current_frequency + 100))

# AF Gain slider
slider_frame = Frame(window)
slider_frame.grid(column=6, row=0, rowspan=3, padx=2, pady=(18,2))
volume_slider = Scale(slider_frame, from_=63, to=0, orient=VERTICAL, length=110, command=lambda value: set_volume(int(value)))
volume_slider.set(current_volume)
volume_slider.pack()

# Extra memory dropdowns als OptionMenu
extra1_var = create_memory_menu(EXTRA_1_MEMORIES, "HAM BANDS", 2)
extra2_var = create_memory_menu(EXTRA_2_MEMORIES, "BROADCAST", 4)

# Memory buttons
memory_buttons = []
for idx, (freq, mode) in enumerate(FIXED_MEMORIES):
    row_number = 2 + (idx // 6)
    column_number = 2 + idx 
    btn = Button(window, text=str(freq // 1000), bg="orange", command=lambda f=freq, m=mode: set_memory(f, m), width=8)
    btn.grid(column=column_number, row=row_number, pady=4, padx=(2, 2))
    memory_buttons.append(btn)

dx_list = Listbox(window, height=10, font=("Consolas", 12))
dx_list.grid(row=5, column=0, columnspan=7, sticky="ew", padx=(42,2), pady=5)
dx_list.bind("<Double-Button-1>", dx_double_click)

# S-meter balk
smeter_canvas = Canvas(
    window,
    width=266,
    height=50,
    bg="black",
    highlightthickness=0
)

smeter_canvas.grid(
    column=0,
    row=0,
    columnspan=2,
    padx=(40,2),
    pady=(10,2)
)

# Automatic update for ever routine
update_status()
update_smeter()
update_dx_window()
window.after(500, start_dxcluster)

window.mainloop()
