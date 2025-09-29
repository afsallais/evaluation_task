import serial  # For UART communication with STM32
import matplotlib.pyplot as plt  # For plotting data
import matplotlib.animation as animation  # For real-time plot updates
from collections import deque  # Efficient queue for fixed-length data storage
import numpy as np  # For numerical operations (frequency estimation)
from matplotlib.widgets import Button  # For pause/resume button

# -----------------------------
# Serial configuration
# -----------------------------
ser = serial.Serial('COM13', 921600, timeout=0.1)  # Open COM13, baud 921600, 0.1s timeout

# -----------------------------
# Plot configuration
# -----------------------------
max_points = 200  # Number of samples displayed in sliding window
y_data = deque([0]*max_points, maxlen=max_points)  # Y-values deque initialized with zeros
x_data = deque(range(max_points), maxlen=max_points)  # X-values as sample indices

fig, ax = plt.subplots()  # Create figure and axes for plotting
plt.subplots_adjust(bottom=0.2)  # Leave space at bottom for pause/resume button

line, = ax.plot(x_data, y_data, color='blue')  # Initial line plot
legend_text = ax.text(0.7, 1.05, '', transform=ax.transAxes)  # Text above plot for Vpp and frequency
ax.set_ylim(0, 255)  # Y-axis limits assuming 8-bit ADC
ax.set_xlabel("Samples")  # X-axis label
ax.set_ylabel("Amplitude")  # Y-axis label
ax.set_title("Real-time Data from STM32")  # Plot title
ax.grid(True)  # Enable grid for better readability

# -----------------------------
# Pause/resume button
# -----------------------------
paused = False  # Boolean flag to track pause state

def toggle_pause(event):
    """Toggle pause state when button is clicked."""
    global paused
    paused = not paused  # Switch paused flag
    if paused:
        btn.label.set_text("Resume")  # Change button label to Resume
    else:
        btn.label.set_text("Pause")  # Change button label back to Pause

ax_button = plt.axes([0.8, 0.05, 0.1, 0.075])  # Button position (x, y, width, height)
btn = Button(ax_button, 'Pause')  # Create pause button
btn.on_clicked(toggle_pause)  # Connect button click to toggle function

# -----------------------------
# Checksum verification
# -----------------------------
def verify_checksum(data, checksum):
    """Verify XOR checksum of packet."""
    cs = 0  # Initialize checksum
    for b in data:
        cs ^= b  # XOR all payload bytes
    return cs == checksum  # True if checksum matches

# -----------------------------
# Extract a single packet from buffer
# -----------------------------
def extract_packet(buffer):
    """Finds complete packet in buffer. Returns packet and remaining buffer."""
    print(buffer)
    start_index = buffer.find(b'\xAA')  # Look for start byte 0xAA
    # todo take time store globally, take difference
    if start_index == -1:  # Start byte not found
        return None, buffer
    if len(buffer) < start_index + 3:  # Minimum packet size: start + length + checksum
        return None, buffer
    length = buffer[start_index + 1]  # Read payload length
    if len(buffer) < start_index + 2 + length + 1:  # Full packet not yet received
        return None, buffer
    packet = buffer[start_index:start_index + 2 + length + 1]  # Extract full packet (start + length + payload + checksum)
    remaining = buffer[start_index + 2 + length + 1:]  # Remaining bytes after packet
    return packet, remaining

# -----------------------------
# Frequency estimation
# -----------------------------
def estimate_frequency(y_values, sample_rate):
    """Estimate frequency using zero-crossings method."""
    y_array = np.array(y_values)  # Convert deque to numpy array
    mean_val = np.mean(y_array)  # Center waveform around zero
    crossings = np.where(np.diff(np.sign(y_array - mean_val)) > 0)[0]  # Rising zero-crossings
    if len(crossings) < 2:  # Not enough crossings to estimate frequency
        return 0
    period_samples = np.mean(np.diff(crossings))  # Average samples per period
    freq = sample_rate / period_samples  # Convert to Hz
    return freq

# -----------------------------
# Animation update function
# -----------------------------
buffer = bytearray()  # Byte buffer to store incoming UART data
SAMPLE_RATE = 10000  # STM32 sampling rate in Hz

def update(frame):
    """Read UART, parse packets, update plot and frequency/amplitude display."""
    global buffer, paused
    try:
        buffer += ser.read(ser.in_waiting or 1)  # Read available bytes from UART

        if not paused:  # Only process buffer if not paused
            while True:
                packet, buffer = extract_packet(buffer)  # Extract next complete packet
                if packet is None:
                    break  # No full packet yet

                data = packet[2:-1]  # Extract payload
                checksum = packet[-1]  # Extract checksum

                if verify_checksum(data, checksum):
                    y_data.extend(data)  # Append payload to plot data
                else:
                    print("Checksum failed:", list(packet))  # Print failed packet

    except Exception as e:
        print("Error:", e)  # Print exceptions if any

    line.set_ydata(y_data)  # Update line plot with new data

    # Dynamically adjust Y-axis
    y_min = min(y_data)
    y_max = max(y_data)
    ax.set_ylim(y_min - 5, y_max + 5)

    # Compute Peak-to-Peak and estimated frequency
    vpp = y_max - y_min
    freq = estimate_frequency(y_data, SAMPLE_RATE)
    legend_text.set_text(f'Peak-to-Peak={vpp:.1f}, Freq={freq:.1f} Hz')  # Update text display

    return line, legend_text  # Return updated objects to FuncAnimation

# -----------------------------
# Run animation
# -----------------------------
ani = animation.FuncAnimation(fig, update, interval=10, blit=False)  # Update every 10 ms
plt.show()  # Display interactive plot window
