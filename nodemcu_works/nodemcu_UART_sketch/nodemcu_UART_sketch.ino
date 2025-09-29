#include <Arduino.h>
#include <math.h>

float amplitude = 100.0;
float frequency = 1000.0; // 1 kHz sine
float time_sec = 0.0;

// Send one sample as a packet: [start][length][data][checksum]
void sendSamplePacket(uint8_t sample) {
  uint8_t startByte = 0xAA;     
  uint8_t length = 1;           
  uint8_t checksum = sample;    

  Serial.write(startByte);
  Serial.write(length);
  Serial.write(sample);
  Serial.write(checksum);
}

void setup() {
  Serial.begin(921600); // High baud rate for more samples
}

void loop() {
  // Compute sine wave
  float y = amplitude * sin(2 * PI * frequency * time_sec);
  uint8_t plotValue = (uint8_t)(y + amplitude); // shift to 0–200

  // Send over UART
  sendSamplePacket(plotValue);

  // Increment time for 16 samples per cycle
  time_sec += 1.0 / (frequency * 16); // 16 kHz sampling
}
