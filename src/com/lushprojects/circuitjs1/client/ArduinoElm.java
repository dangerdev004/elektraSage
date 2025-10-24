package com.lushprojects.circuitjs1.client;

import java.util.StringTokenizer;

class ArduinoElm extends ChipElm {
    // Pin indices for all Arduino Uno pins
    final int N_D0 = 0;
    final int N_D1 = 1;
    final int N_D2 = 2;
    final int N_D3 = 3;
    final int N_D4 = 4;
    final int N_D5 = 5;
    final int N_D6 = 6;
    final int N_D7 = 7;
    final int N_D8 = 8;
    final int N_D9 = 9;
    final int N_D10 = 10;
    final int N_D11 = 11;
    final int N_D12 = 12;
    final int N_D13 = 13;
    final int N_A0 = 14;
    final int N_A1 = 15;
    final int N_A2 = 16;
    final int N_A3 = 17;
    final int N_A4 = 18;
    final int N_A5 = 19;
    final int N_VCC = 20;
    final int N_GND = 21;
    
    // Arduino constants
    final int INPUT = 0;
    final int OUTPUT = 1;
    final int INPUT_PULLUP = 2;
    final int HIGH = 1;
    final int LOW = 0;
    
    // Pin state arrays
    int[] pinModes = new int[20];
    boolean[] pinStates = new boolean[20];
    int[] analogValues = new int[6]; // 10-bit ADC values (0-1023)
    int[] pwmValues = new int[6]; // PWM capable pins: 3,5,6,9,10,11
    boolean[] pwmEnabled = new boolean[6];
    
    // Timing
    long simulationTime = 0; // in microseconds
    long lastExecuteTime = 0;
    final long EXECUTE_INTERVAL = 100; // Execute Arduino logic every 100us
    
    // Serial buffer (simplified)
    StringBuilder serialBuffer = new StringBuilder();
    
    int ground;
    double vcc = 5.0;
    
    public ArduinoElm(int xx, int yy) { 
        super(xx, yy);
        for (int i = 0; i < 20; i++) {
            pinModes[i] = INPUT;
            pinStates[i] = false;
        }
        for (int i = 0; i < 6; i++) {
            analogValues[i] = 0;
            pwmValues[i] = 0;
            pwmEnabled[i] = false;
        }
    }
    
    String getChipName() { return "Arduino Uno"; }
    
    void setupPins() {
        sizeX = 6;
        sizeY = 11;
        pins = new Pin[22];
        
        // Left side - Digital pins D0-D7
        pins[N_D0] = new Pin(0, SIDE_W, "D0");
        pins[N_D1] = new Pin(1, SIDE_W, "D1");
        pins[N_D2] = new Pin(2, SIDE_W, "D2");
        pins[N_D3] = new Pin(3, SIDE_W, "~D3");  // ~ indicates PWM
        pins[N_D4] = new Pin(4, SIDE_W, "D4");
        pins[N_D5] = new Pin(5, SIDE_W, "~D5");
        pins[N_D6] = new Pin(6, SIDE_W, "~D6");
        pins[N_D7] = new Pin(7, SIDE_W, "D7");
        
        // Right side - Digital pins D8-D13
        pins[N_D8] = new Pin(0, SIDE_E, "D8");
        pins[N_D9] = new Pin(1, SIDE_E, "~D9");
        pins[N_D10] = new Pin(2, SIDE_E, "~D10");
        pins[N_D11] = new Pin(3, SIDE_E, "~D11");
        pins[N_D12] = new Pin(4, SIDE_E, "D12");
        pins[N_D13] = new Pin(5, SIDE_E, "D13");
        
        // Bottom - Analog pins
        pins[N_A0] = new Pin(0, SIDE_S, "A0");
        pins[N_A1] = new Pin(1, SIDE_S, "A1");
        pins[N_A2] = new Pin(2, SIDE_S, "A2");
        pins[N_A3] = new Pin(3, SIDE_S, "A3");
        pins[N_A4] = new Pin(4, SIDE_S, "A4");
        pins[N_A5] = new Pin(5, SIDE_S, "A5");
        
        // Top - Power
        pins[N_VCC] = new Pin(2, SIDE_N, "5V");
        pins[N_GND] = new Pin(3, SIDE_N, "GND");
    }
    
    boolean nonLinear() { return true; }
    
    @Override 
    boolean isDigitalChip() { return false; }
    
    void stamp() {
        ground = nodes[N_GND];
        
        // Stamp all pins as non-linear
        for (int i = 0; i < 20; i++) {
            sim.stampNonLinear(nodes[i]);
        }
        
        sim.stampNonLinear(nodes[N_VCC]);
        sim.stampNonLinear(nodes[N_GND]);
    }
    
    void calculateCurrent() {
        double totalCurrent = 0;
        double pinResistance = 40; // Arduino output pin resistance ~40 ohms
        
        for (int i = 0; i < 14; i++) { // Digital pins
            if (pinModes[i] == OUTPUT) {
                if (pinStates[i]) {
                    pins[i].current = (volts[N_VCC] - volts[i]) / pinResistance;
                } else {
                    pins[i].current = (volts[i] - volts[N_GND]) / pinResistance;
                }
                totalCurrent += Math.abs(pins[i].current);
            } else {
                pins[i].current = 0;
            }
        }
        
        // Add quiescent current (Arduino itself draws ~50mA)
        totalCurrent += 0.05;
        
        pins[N_VCC].current = -totalCurrent;
        pins[N_GND].current = totalCurrent;
    }
    
    void startIteration() {
        double groundVolts = volts[N_GND];
        double vccVolts = volts[N_VCC];
        vcc = vccVolts - groundVolts;
        
        // Read digital input pins
        for (int i = 0; i < 14; i++) {
            if (pinModes[i] == INPUT || pinModes[i] == INPUT_PULLUP) {
                double threshold = vcc / 2;
                if (pinModes[i] == INPUT_PULLUP) {
                    threshold = vcc * 0.3; // Lower threshold with pullup
                }
                pinStates[i] = (volts[i] - groundVolts) > threshold;
            }
        }
        
        // Read analog input pins (A0-A5)
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            double voltage = volts[pinIdx] - groundVolts;
            voltage = Math.max(0, Math.min(vcc, voltage)); // Clamp to 0-Vcc
            analogValues[i] = (int)((voltage / vcc) * 1023); // 10-bit ADC
        }
        
        // Update simulation time
        simulationTime += (long)(sim.timeStep * 1000000);
        
        // Execute Arduino logic at fixed intervals
        if (simulationTime - lastExecuteTime >= EXECUTE_INTERVAL) {
            execute();
            lastExecuteTime = simulationTime;
        }
    }
    
    void doStep() {
        double pinResistance = 40;
        double pullupResistance = 20000; // 20K pullup
        
        for (int i = 0; i < 14; i++) {
            if (pinModes[i] == OUTPUT) {
                // Check if PWM is enabled for this pin
                int pwmIdx = getPWMIndex(i);
                if (pwmIdx >= 0 && pwmEnabled[pwmIdx]) {
                    // Simulate PWM with average voltage
                    double dutyCycle = pwmValues[pwmIdx] / 255.0;
                    double targetVoltage = volts[N_GND] + vcc * dutyCycle;
                    // Use low resistance to drive pin
                    sim.stampResistor(nodes[N_VCC], nodes[i], 
                        pinResistance * (1.0 / dutyCycle));
                } else {
                    // Normal digital output
                    if (pinStates[i]) {
                        sim.stampResistor(nodes[N_VCC], nodes[i], pinResistance);
                    } else {
                        sim.stampResistor(nodes[i], ground, pinResistance);
                    }
                }
            } else if (pinModes[i] == INPUT_PULLUP) {
                // Pullup resistor to Vcc
                sim.stampResistor(nodes[N_VCC], nodes[i], pullupResistance);
            } else {
                // High impedance for normal inputs
                sim.stampResistor(nodes[i], ground, 1e9);
            }
        }
        
        // Analog pins when used as digital
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            int logicalPin = 14 + i;
            if (pinModes[logicalPin] == OUTPUT) {
                if (pinStates[logicalPin]) {
                    sim.stampResistor(nodes[N_VCC], nodes[pinIdx], pinResistance);
                } else {
                    sim.stampResistor(nodes[pinIdx], ground, pinResistance);
                }
            } else {
                sim.stampResistor(nodes[pinIdx], ground, 1e9);
            }
        }
    }
    
    // Helper to get PWM index for a pin
    int getPWMIndex(int pin) {
        switch(pin) {
            case 3: return 0;
            case 5: return 1;
            case 6: return 2;
            case 9: return 3;
            case 10: return 4;
            case 11: return 5;
            default: return -1;
        }
    }
    
    // ===== ARDUINO API =====
    
    void pinMode(int pin, int mode) {
        if (pin >= 0 && pin < 20) {
            pinModes[pin] = mode;
        }
    }
    
    void digitalWrite(int pin, int value) {
        if (pin >= 0 && pin < 20 && pinModes[pin] == OUTPUT) {
            pinStates[pin] = (value == HIGH);
            // Disable PWM if it was enabled
            int pwmIdx = getPWMIndex(pin);
            if (pwmIdx >= 0) {
                pwmEnabled[pwmIdx] = false;
            }
        }
    }
    
    int digitalRead(int pin) {
        if (pin >= 0 && pin < 20) {
            return pinStates[pin] ? HIGH : LOW;
        }
        return LOW;
    }
    
    int analogRead(int pin) {
        // pin can be 0-5 for A0-A5, or 14-19 for same
        if (pin >= 0 && pin < 6) {
            return analogValues[pin];
        } else if (pin >= 14 && pin < 20) {
            return analogValues[pin - 14];
        }
        return 0;
    }
    
    void analogWrite(int pin, int value) {
        int pwmIdx = getPWMIndex(pin);
        if (pwmIdx >= 0 && pinModes[pin] == OUTPUT) {
            pwmValues[pwmIdx] = Math.max(0, Math.min(255, value));
            pwmEnabled[pwmIdx] = true;
        }
    }
    
    long millis() {
        return simulationTime / 1000;
    }
    
    long micros() {
        return simulationTime;
    }
    
    void delay(long ms) {
        // Note: In simulation, delay is non-blocking
        // This is just for API compatibility
    }
    
    // Simplified serial output
    void serialPrint(String str) {
        serialBuffer.append(str);
        System.out.println("Arduino Serial: " + str);
    }
    
    void serialPrintln(String str) {
        serialPrint(str + "\n");
    }
    
    // ===== USER CODE =====
    // Override this method to implement your Arduino sketch
    void execute() {
        // Example: Blink LED on D13
        if ((millis() / 1000) % 2 == 0) {
            pinMode(13, OUTPUT);
            digitalWrite(13, HIGH);
        } else {
            digitalWrite(13, LOW);
        }
    }
    
    // Optional: setup() called once at start
    void setup() {
        // Override in subclass
    }
    
    // Optional: loop() called repeatedly
    void loop() {
        // Override in subclass
    }
    
    int getPostCount() { return 22; }
    int getVoltageSourceCount() { return 0; }
    int getDumpType() { return 400; }
}