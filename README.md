```markdown
# Coffee Roaster Auto Control

Embedded firmware for an **automatic coffee roasting machine** built on **STM32 + PlatformIO + Arduino framework**.

This project controls the roasting process including **temperature monitoring, burner power control, airflow control, and roasting data logging**.  
It is designed to support **stable roast profiles** and future **AI-assisted control algorithms**.

---

## Hardware Platform

**Microcontroller**

STM32F103RC

**Development Environment**

PlatformIO  
Arduino Framework

**Typical Hardware Setup**

- STM32F103 controller board
- Temperature sensor (Thermocouple / RTD)
- Pressure sensor
- Gas burner control
- Fan / airflow control
- I2C DAC output
- RS485 Modbus sensors
- SD card for roast data logging

---

## Project Structure

```

coffee-roaster-auto-control
│
├── src
│   └── main.cpp
│
├── include
│
├── lib
│
├── platformio.ini
│
├── Temp
│
└── test

```

---

## Dependencies

This project uses the following libraries:

- **SD** – Roast data logging
- **ModbusMaster** – RS485 communication with external sensors
- **Adafruit MCP4725** – I2C DAC for analog actuator control
- **SimpleKalmanFilter** – Sensor signal filtering

Libraries are automatically installed by PlatformIO.

---

## Control Workflow

Typical control loop:

1. Read sensor data  
2. Filter measurements  
3. Calculate control output  
4. Adjust burner power  
5. Adjust fan speed  
6. Log roasting data  

---

## Build Firmware

```

pio run

```

---

## Upload Firmware

```

pio run --target upload

```

---

## Serial Monitor

```

pio device monitor

```

---

## Future Development

- Advanced PID control
- ROR (Rate of Rise) roasting control
- Adaptive burner control
- AI-assisted PID tuning
- Automatic roast profile optimization

---

## Author

TCL-DA  
Coffee Roaster Automation Project
```
