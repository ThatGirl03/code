import tkinter as tk
from tkinter import messagebox
import paho.mqtt.client as mqtt
from paho import mqtt as paho_mqtt
import cv2
import datetime
import threading

# Variables for storing scores and timer
score_player1 = 0
score_player2 = 0
time_remaining = 120  # 2 minutes = 120 seconds
running = False
recording_paused = False

# MQTT broker details
BROKER_URL = "32747989fbc243fa8e6939c37b4e6371.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "ndleko"
MQTT_PASSWORD = "12345678"

# MQTT topics for all judges
MQTT_TOPICS = {
    "judge1/player1": "player1",
    "judge1/player2": "player2",
    "judge2/player1": "player1",
    "judge2/player2": "player2",
    "judge3/player1": "player1",
    "judge3/player2": "player2"
}

# Variables for video recording
cap = cv2.VideoCapture(0)
camera_available = cap.isOpened()

if camera_available:
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = cv2.VideoWriter(f'match_record_{timestamp}.avi', fourcc, 20.0, (640, 480))

# Functions for the timer
def start_timer():
    global running, recording_paused
    if not running:
        running = True
        recording_paused = False
        countdown()
        if camera_available:
            start_video_recording()

def stop_timer():
    global running, recording_paused
    running = False
    recording_paused = True

def reset():
    global score_player1, score_player2, time_remaining
    score_player1 = 0
    score_player2 = 0
    time_remaining = 120
    update_display()
    time_label.config(text="02:00")
    player1_name_entry.delete(0, tk.END)
    player2_name_entry.delete(0, tk.END)
    player1_dojo_entry.delete(0, tk.END)
    player2_dojo_entry.delete(0, tk.END)

def countdown():
    global time_remaining
    if running and time_remaining > 0:
        mins, secs = divmod(time_remaining, 60)
        time_label.config(text=f"{mins:02d}:{secs:02d}")
        time_remaining -= 1
        time_label.after(1000, countdown)
    elif time_remaining == 0:
        stop_timer()
        declare_winner()

def declare_winner():
    if score_player1 > score_player2:
        winner = player1_name_entry.get()
    elif score_player2 > score_player1:
        winner = player2_name_entry.get()
    else:
        winner = "Draw"
    messagebox.showinfo("Match Result", f"The winner is: {winner}")

# Functions for updating scores
def update_display():
    score_label_player1.config(text=score_player1)
    score_label_player2.config(text=score_player2)

# MQTT callback functions
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    for topic in MQTT_TOPICS:
        client.subscribe(topic, qos=1)

def on_message(client, userdata, msg):
    global score_player1, score_player2
    print(f"Received message on topic '{msg.topic}' with QoS {msg.qos}:\n\t>> '{msg.payload.decode()}'")

    if MQTT_TOPICS[msg.topic] == "player1":
        score_player1 += 1
    elif MQTT_TOPICS[msg.topic] == "player2":
        score_player2 += 1
    update_display()

# Function for video recording
def start_video_recording():
    threading.Thread(target=record_video, daemon=True).start()

def record_video():
    global recording_paused
    while running or not recording_paused:
        if camera_available and not recording_paused:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
            else:
                break
        cv2.waitKey(1)

# Clean up function for closing video capture
def on_closing():
    if camera_available:
        cap.release()
        out.release()
    cv2.destroyAllWindows()
    root.destroy()

# MQTT setup
client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_connect = on_connect
client.on_message = on_message
client.tls_set(tls_version=paho_mqtt.client.ssl.PROTOCOL_TLS)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Create the Tkinter GUI
root = tk.Tk()
root.title("Karate Scoring System")

# Player 1 panel
player1_frame = tk.Frame(root, bg="blue")
player1_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
tk.Label(player1_frame, text="Player 1", fg="white", bg="blue", font=("Arial", 20)).pack()
player1_name_entry = tk.Entry(player1_frame, font=("Arial", 18))
player1_name_entry.pack(pady=5)
player1_dojo_entry = tk.Entry(player1_frame, font=("Arial", 16))
player1_dojo_entry.pack(pady=5)
score_label_player1 = tk.Label(player1_frame, text="0", fg="white", bg="blue", font=("Arial", 40))
score_label_player1.pack(pady=20)

# Player 2 panel
player2_frame = tk.Frame(root, bg="red")
player2_frame.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
tk.Label(player2_frame, text="Player 2", fg="white", bg="red", font=("Arial", 20)).pack()
player2_name_entry = tk.Entry(player2_frame, font=("Arial", 18))
player2_name_entry.pack(pady=5)
player2_dojo_entry = tk.Entry(player2_frame, font=("Arial", 16))
player2_dojo_entry.pack(pady=5)
score_label_player2 = tk.Label(player2_frame, text="0", fg="white", bg="red", font=("Arial", 40))
score_label_player2.pack(pady=20)

# Timer and controls panel
controls_frame = tk.Frame(root)
controls_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
time_label = tk.Label(controls_frame, text="02:00", font=("Arial", 30))
time_label.pack(pady=10)
start_button = tk.Button(controls_frame, text="Start", command=start_timer, font=("Arial", 14))
start_button.pack(pady=5)
stop_button = tk.Button(controls_frame, text="Stop", command=stop_timer, font=("Arial", 14))
stop_button.pack(pady=5)
reset_button = tk.Button(controls_frame, text="Reset", command=reset, font=("Arial", 14))
reset_button.pack(pady=5)

# Configure window resizing
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure([0, 1, 2], weight=1)

# Connect to MQTT broker
try:
    client.connect(BROKER_URL, MQTT_PORT)
    client.loop_start()
except Exception as e:
    print(f"Error connecting to MQTT broker: {e}")
    messagebox.showerror("Error", "Unable to connect to MQTT broker")

# Set up GUI window closing to release resources
root.protocol("WM_DELETE_WINDOW", on_closing)

# Start the GUI loop
root.mainloop()
