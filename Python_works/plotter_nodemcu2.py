import serial  # For communicating with STM32 via UART
import matplotlib.pyplot as plt  # For plotting data
import matplotlib.animation as animation  # For real-time animation updates
from collections import deque  # Efficient queue for fixed-length data storage
import numpy as np  # For numerical operations, used in frequency estimation
from matplotlib.widgets import Button  # For creating a pause/resume button

# -----------------------------
# Serial configuration
# -----------------------------
ser = serial.Serial('COM14', 921600, timeout=0.1)  # Open serial port COM14, baud rate 921600, timeout 0.1s

# -----------------------------
# Plot configuration
# -----------------------------
max_points = 200  # Number of points to display in the sliding window of the plot
y_data = deque([0]*max_points, maxlen=max_points)  # Initialize y-values with zeros
x_data = deque(range(max_points), maxlen=max_points)  # x-values as sample indices (0..199)

fig, ax = plt.subplots()  # Create figure and axes for plotting
plt.subplots_adjust(bottom=0.2)  # Make space at bottom for pause/resume button
line, = ax.plot(x_data, y_data, color='blue')  # Plot initial line, store reference for updates
legend_text = ax.text(0.7, 1.05, '', transform=ax.transAxes)  # Text for displaying Peak-to-Peak and frequency
ax.set_ylim(0, 255)  # Set initial Y-axis limits (assuming 8-bit ADC data)
ax.set_xlabel("Samples")  # Label X-axis
ax.set_ylabel("Amplitude")  # Label Y-axis
ax.set_title("Real-time Data from NodeMCU")  # Plot title
ax.grid(True)  # Enable grid

# -----------------------------
# Pause/resume button
# -----------------------------
paused = False  # Boolean flag to track pause/resume state

def toggle_pause(event):
    """Toggle the paused state when the button is clicked."""
    global paused
    paused = not paused  # Flip paused flag
    if paused:
        btn.label.set_text("Resume")  # Change button text to 'Resume' when paused
    else:
        btn.label.set_text("Pause")  # Change button text back to 'Pause' when resumed

ax_button = plt.axes([0.8, 0.05, 0.1, 0.075])  # Define button position (x, y, width, height)
btn = Button(ax_button, 'Pause')  # Create button labeled 'Pause'
btn.on_clicked(toggle_pause)  # Link button click to toggle_pause function

# -----------------------------
# Checksum verification
# -----------------------------
def verify_checksum(data, checksum):
    """
    Verify a simple XOR checksum.
    data: list/bytes of payload
    checksum: byte value received
    """
    cs = 0  # Initialize checksum variable
    for b in data:
        cs ^= b  # XOR each data byte
    return cs == checksum  # Return True if computed checksum matches received one

# -----------------------------
# Frequency estimation
# -----------------------------
def estimate_frequency(y_values, sample_rate):
    """
    Estimate frequency using zero-crossings method.
    y_values: deque/list of signal amplitudes
    sample_rate: sampling frequency in Hz
    """
    y_array = np.array(y_values)  # Convert deque to NumPy array
    mean_val = np.mean(y_array)  # Compute mean to center the waveform
    crossings = np.where(np.diff(np.sign(y_array - mean_val)) > 0)[0]  # Detect rising zero-crossings
    if len(crossings) < 2:  # If fewer than 2 crossings, cannot estimate frequency
        return 0
    period_samples = np.mean(np.diff(crossings))  # Average number of samples per period
    freq = sample_rate / period_samples  # Convert period to frequency in Hz
    return freq

# -----------------------------
# Animation update function
# -----------------------------
buffer = bytearray()  # Buffer to store incoming UART bytes
SAMPLE_RATE = 10000  # Sampling rate of STM32 in Hz

def update(frame):
    """
    Update function called by FuncAnimation every interval.
    Reads serial data, parses packets, updates plot and legend text.
    """
    global buffer, paused
    try:
        # Read all available bytes from UART; if none, read at least 1
        buffer += ser.read(ser.in_waiting or 1)

        if not paused:  # Only update the plot if not paused
            while True:
                if len(buffer) < 3:  # Minimum packet size: start + length + checksum
                    break

                if buffer[0] != 0xAA:  # Sync to start byte 0xAA
                    buffer.pop(0)  # Remove first byte until start byte found
                    continue

                length = buffer[1]  # Second byte indicates payload length
                if len(buffer) < 2 + length + 1:  # Full packet not yet received
                    break

                data = buffer[2:2+length]  # Extract payload bytes
                checksum = buffer[2+length]  # Extract checksum byte

                if verify_checksum(data, checksum):  # Validate packet
                    y_data.extend(data)  # Append payload to y_data
                else:
                    print("Checksum failed:", list(buffer[:2+length+1]))  # Print failed packet

                buffer = buffer[2+length+1:]  # Remove processed packet from buffer

    except Exception as e:
        print("Error:", e)  # Print any exceptions

    line.set_ydata(y_data)  # Update line y-values for plot

    # Compute peak-to-peak amplitude and estimated frequency
    vpp = max(y_data) - min(y_data)
    freq = estimate_frequency(y_data, SAMPLE_RATE)

    legend_text.set_text(f'Peak-to-Peak={vpp:.1f}, Freq={freq:.1f} Hz')  # Update legend text

    return line, legend_text  # Return updated plot objects

# -----------------------------
# Run animation
# -----------------------------
ani = animation.FuncAnimation(fig, update, interval=10, blit=False)  # Call update every 10 ms
plt.show()  # Display interactive plot window
