import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# -----------------------------
# Serial configuration
# -----------------------------
ser = serial.Serial('COM7', 115200, timeout=0.1)  # match STM32 baud rate

# -----------------------------
# Plot configuration
# -----------------------------
max_points = 200
y_data = deque([0]*max_points, maxlen=max_points)
x_data = deque(range(max_points), maxlen=max_points)

fig, ax = plt.subplots()
line, = ax.plot(x_data, y_data)
ax.set_ylim(0, 255)  # adjust based on your data
ax.set_xlabel("Samples")
ax.set_ylabel("Amplitude")
ax.set_title("Real-time Data from STM32")

# -----------------------------
# Checksum verification
# -----------------------------
def verify_checksum(data, checksum):
    cs = 0
    for b in data:
        cs ^= b
    return cs == checksum

# -----------------------------
# Animation update function
# -----------------------------
buffer = bytearray()

def update(frame):
    global buffer
    try:
        buffer += ser.read(ser.in_waiting or 1)  # read available bytes

        while True:
            if len(buffer) < 3:  # at least start + length + checksum
                break

            # sync to start byte 0xAA
            if buffer[0] != 0xAA:
                buffer.pop(0)
                continue

            length = buffer[1]
            if len(buffer) < 2 + length + 1:  # full packet not received
                break

            data = buffer[2:2+length]
            checksum = buffer[2+length]

            if verify_checksum(data, checksum):
                for sample in data:
                    y_data.append(sample)
                # optionally, print or log data
                # print(list(data))
            else:
                print("Checksum failed for packet:", list(buffer[:2+length+1]))

            # remove processed packet from buffer
            buffer = buffer[2+length+1:]

    except Exception as e:
        print("Error:", e)

    line.set_ydata(y_data)
    return line,

# -----------------------------
# Run animation
# -----------------------------
ani = animation.FuncAnimation(fig, update, interval=10, blit=True)
plt.show()
