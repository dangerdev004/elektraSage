package com.lushprojects.circuitjs1.client;

import com.google.gwt.typedarrays.shared.Uint8Array;
import com.google.gwt.user.client.ui.Button;

/**
 * Arduino Uno element with AVR8JS emulation
 * Runs real Arduino code compiled to hex files
 */
class ArduinoElm extends ChipElm {
    
    // Pin indices for Arduino Uno
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
    
    // Pin state tracking
    boolean[] pinStates = new boolean[20];
    int[] analogValues = new int[6]; // 10-bit ADC (0-1023)
    
    // UI / mode options
    int vccChoiceIndex = 0; // 0 = 5V, 1 = 3.3V
    boolean useFixedVcc = false; // when true, use selected VCC instead of circuit VCC node
    boolean serialEnabled = true; // enable/disable serial output

    
    // Serial output buffer
    private StringBuilder serialBuffer = new StringBuilder();
    
    // Circuit properties
    int ground;
    double vcc = 5.0;
    
    public ArduinoElm(int xx, int yy) { 
        super(xx, yy);
        for (int i = 0; i < 20; i++) {
            pinStates[i] = false;
        }
        for (int i = 0; i < 6; i++) {
            analogValues[i] = 0;
        }
        // defaults for options
        vccChoiceIndex = 0;
        useFixedVcc = false;
        serialEnabled = true;
    }
    
    String getChipName() { return "Arduino Uno"; }
    
    void setupPins() {
        sizeX = 7;  // Width - adjusted for better proportions
        sizeY = 14; // Height - taller to fit all digital pins on right side
        pins = new Pin[22];
        
        // TOP - Power supply (5V)
        pins[N_VCC] = new Pin(3, SIDE_N, "5V");
        
        // BOTTOM - Ground (GND)
        pins[N_GND] = new Pin(3, SIDE_S, "GND");
        
        // LEFT SIDE - Analog pins A0-A5
        pins[N_A0] = new Pin(6, SIDE_W, "A0");
        pins[N_A1] = new Pin(7, SIDE_W, "A1");
        pins[N_A2] = new Pin(8, SIDE_W, "A2");
        pins[N_A3] = new Pin(9, SIDE_W, "A3");
        pins[N_A4] = new Pin(10, SIDE_W, "A4");
        pins[N_A5] = new Pin(11, SIDE_W, "A5");
        
        // RIGHT SIDE - Digital pins D13 down to D0 (RX/TX)
        // From top to bottom: D13, D12, D11, D10, D9, D8, D7, D6, D5, D4, D3, D2, TX(D1), RX(D0)
        pins[N_D13] = new Pin(0, SIDE_E, "13");
        pins[N_D12] = new Pin(1, SIDE_E, "12");
        pins[N_D11] = new Pin(2, SIDE_E, "11");
        pins[N_D10] = new Pin(3, SIDE_E, "10");
        pins[N_D9] = new Pin(4, SIDE_E, "~9");
        pins[N_D8] = new Pin(5, SIDE_E, "8");
        pins[N_D7] = new Pin(6, SIDE_E, "7");
        pins[N_D6] = new Pin(7, SIDE_E, "~6");
        pins[N_D5] = new Pin(8, SIDE_E, "~5");
        pins[N_D4] = new Pin(9, SIDE_E, "4");
        pins[N_D3] = new Pin(10, SIDE_E, "~3");
        pins[N_D2] = new Pin(11, SIDE_E, "2");
        pins[N_D1] = new Pin(12, SIDE_E, "(TX)1");
        pins[N_D0] = new Pin(13, SIDE_E, "(RX)0");
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
        double pinResistance = 40; // Output pin resistance ~40 ohms
        
        // Calculate current for output pins
        for (int i = 0; i < 14; i++) { // Digital pins D0-D13
            if (pinStates[i]) { // If pin is HIGH
                pins[i].current = (volts[N_VCC] - volts[i]) / pinResistance;
            } else {
                pins[i].current = (volts[i] - volts[N_GND]) / pinResistance;
            }
            totalCurrent += Math.abs(pins[i].current);
        }
        
        // Add quiescent current (Arduino ~50mA)
        totalCurrent += 0.05;
        
        pins[N_VCC].current = -totalCurrent;
        pins[N_GND].current = totalCurrent;
    }
    
    void startIteration() {
        // Read voltages
        double groundVolts = volts[N_GND];
        double vccVolts = volts[N_VCC];
        if (useFixedVcc) {
            vcc = (vccChoiceIndex == 0) ? 5.0 : 3.3;
        } else {
            vcc = vccVolts - groundVolts;
        }
        
        // Read analog input pins (A0-A5)
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            double voltage = volts[pinIdx] - groundVolts;
            voltage = Math.max(0, Math.min(vcc, voltage)); // Clamp to 0-Vcc
            analogValues[i] = (int)((voltage / vcc) * 1023); // 10-bit ADC
        }
        
    }
    
    void doStep() {
        double pinResistance = 40;
        double highZ = 1e9; // High impedance
        
        // Stamp digital pins based on their state
        for (int i = 0; i < 14; i++) { // D0-D13
            if (pinStates[i]) {
                // Pin is HIGH - connect to VCC through resistance
                sim.stampResistor(nodes[N_VCC], nodes[i], pinResistance);
            } else {
                // Pin is LOW - connect to GND through resistance
                sim.stampResistor(nodes[i], ground, pinResistance);
            }
        }
        
        // Analog pins - high impedance when used for ADC
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            sim.stampResistor(nodes[pinIdx], ground, highZ);
        }
    }
    
    
    
    // ===== Edit dialog support (options/modes) =====

    public EditInfo getEditInfo(int n) {
        if (n == 0) {
            EditInfo ei = new EditInfo("VCC selection", vccChoiceIndex, -1, -1);
            ei.choice = new Choice();
            ei.choice.add("5V");
            ei.choice.add("3.3V");
            ei.choice.select(vccChoiceIndex);
            return ei;
        }
        if (n == 1) {
            return EditInfo.createCheckbox("Use fixed VCC", useFixedVcc);
        }
        if (n == 2) {
            return EditInfo.createCheckbox("Enable Serial Output", serialEnabled);
        }
        return super.getEditInfo(n-3);
    }

    public void setEditValue(int n, EditInfo ei) {
        if (n == 0) {
            vccChoiceIndex = ei.choice.getSelectedIndex();
            if (useFixedVcc) {
                vcc = (vccChoiceIndex == 0) ? 5.0 : 3.3;
            }
        } else if (n == 1) {
            useFixedVcc = ei.checkbox.getState();
            if (useFixedVcc) {
                vcc = (vccChoiceIndex == 0) ? 5.0 : 3.3;
            }
        } else if (n == 2) {
            serialEnabled = ei.checkbox.getState();
            if (!serialEnabled)
                serialBuffer.setLength(0);
        } else {
            super.setEditValue(n-3, ei);
        }
    }

    // ===== UI INTEGRATION =====

    @Override
    public void getInfo(String[] arr) {
        arr[0] = "Arduino Uno (ATmega328P)";
        arr[1] = "CPU: 16 MHz AVR";
        String mode = useFixedVcc ? (vccChoiceIndex == 0 ? " (fixed 5V)" : " (fixed 3.3V)") : " (from circuit)";
        arr[2] = "VCC = " + getVoltageText(vcc) + mode;
        arr[3] = "Serial: " + (serialEnabled ? "enabled" : "disabled") + ", buffer=" + serialBuffer.length() + " bytes";
    }
    
   
    int getPostCount() { return 22; }
    int getVoltageSourceCount() { return 0; }
    int getDumpType() { return 400; }
}