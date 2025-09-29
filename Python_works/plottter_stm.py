import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import numpy as np

# -----------------------------
# Serial configuration
# -----------------------------
ser = serial.Serial('COM6', 921600, timeout=0.1)  # adjust COM port

# -----------------------------
# Plot configuration
# -----------------------------
max_points = 200
y_data = deque([0]*max_points, maxlen=max_points)
x_data = deque(range(max_points), maxlen=max_points)

fig, ax = plt.subplots()
line, = ax.plot(x_data, y_data, color='blue')
legend_text = ax.text(0.7, 1.05, '', transform=ax.transAxes)
ax.set_ylim(0, 255)  # initial guess, will update dynamically
ax.set_xlabel("Samples")
ax.set_ylabel("Amplitude")
ax.set_title("Real-time Data from STM32")
ax.grid(True)

# -----------------------------
# Checksum verification
# -----------------------------
def verify_checksum(data, checksum):
    cs = 0
    for b in data:
        cs ^= b
    return cs == checksum

# -----------------------------
# Extract a single packet from buffer
# -----------------------------
def extract_packet(buffer):
    start_index = buffer.find(b'\xAA')
    if start_index == -1:
        return None, buffer
    if len(buffer) < start_index + 3:
        return None, buffer

    length = buffer[start_index + 1]
    if len(buffer) < start_index + 2 + length + 1:
        return None, buffer

    packet = buffer[start_index:start_index + 2 + length + 1]
    remaining = buffer[start_index + 2 + length + 1:]
    return packet, remaining

# -----------------------------
# Frequency estimation
# -----------------------------
def estimate_frequency(y_values, sample_rate):
    y_array = np.array(y_values)
    mean_val = np.mean(y_array)
    crossings = np.where(np.diff(np.sign(y_array - mean_val)) > 0)[0]
    if len(crossings) < 2:
        return 0
    period_samples = np.mean(np.diff(crossings))
    freq = sample_rate / period_samples
    return freq

# -----------------------------
# Animation update function
# -----------------------------
buffer = bytearray()
SAMPLE_RATE = 10000  # Hz, adjust according to your sampling

def update(frame):
    global buffer
    try:
        buffer += ser.read(ser.in_waiting or 1)

        while True:
            packet, buffer = extract_packet(buffer)
            if packet is None:
                break

            data = packet[2:-1]
            checksum = packet[-1]

            if verify_checksum(data, checksum):
                y_data.extend(data)
            else:
                print("Checksum failed:", list(packet))

    except Exception as e:
        print("Error:", e)

    # Update line
    line.set_ydata(y_data)

    # Update y-axis to fit the data
    y_min = min(y_data)
    y_max = max(y_data)
    ax.set_ylim(y_min - 5, y_max + 5)

    # Compute peak-to-peak and frequency
    vpp = y_max - y_min
    freq = estimate_frequency(y_data, SAMPLE_RATE)

    # Update legend text
    legend_text.set_text(f'Peak-to-Peak={vpp:.1f}, Freq={freq:.1f} Hz')

    return line, legend_text

# -----------------------------
# Run animation
# -----------------------------
ani = animation.FuncAnimation(fig, update, interval=10, blit=False)
plt.show()
