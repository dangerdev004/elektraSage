package com.lushprojects.circuitjs1.client;

import com.lushprojects.circuitjs1.client.Microcontrollers.AVR8JS;
import com.lushprojects.circuitjs1.client.Microcontrollers.AVR8JS.AVRRunner;
import com.lushprojects.circuitjs1.client.Microcontrollers.AVR8JS.PortListener;
import com.lushprojects.circuitjs1.client.Microcontrollers.HexParser;
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
    
    // AVR8JS core
    private AVRRunner avrRunner = null;
    private boolean isRunning = false;
    private double lastSimTime = 0;
    private static final double CPU_FREQ = 16000000.0; // 16 MHz
    
    // Port listeners
    private PortListener portBListener;
    private PortListener portCListener;
    private PortListener portDListener;
    
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
    }
    
    String getChipName() { return "Arduino Uno"; }
    
    void setupPins() {
        sizeX = 8;  // Wider to look more like Arduino board
        sizeY = 14; // Taller to accommodate all pins
        pins = new Pin[22];
        
        // Left side - Digital pins D0-D7
        pins[N_D0] = new Pin(1, SIDE_W, "D0");
        pins[N_D1] = new Pin(2, SIDE_W, "D1");
        pins[N_D2] = new Pin(3, SIDE_W, "D2");
        pins[N_D3] = new Pin(4, SIDE_W, "~D3");
        pins[N_D4] = new Pin(5, SIDE_W, "D4");
        pins[N_D5] = new Pin(6, SIDE_W, "~D5");
        pins[N_D6] = new Pin(7, SIDE_W, "~D6");
        pins[N_D7] = new Pin(8, SIDE_W, "D7");
        
        // Right side - Digital pins D8-D13
        pins[N_D8] = new Pin(1, SIDE_E, "D8");
        pins[N_D9] = new Pin(2, SIDE_E, "~D9");
        pins[N_D10] = new Pin(3, SIDE_E, "~D10");
        pins[N_D11] = new Pin(4, SIDE_E, "~D11");
        pins[N_D12] = new Pin(5, SIDE_E, "D12");
        pins[N_D13] = new Pin(6, SIDE_E, "D13");
        
        // Bottom - Analog pins
        pins[N_A0] = new Pin(1, SIDE_S, "A0");
        pins[N_A1] = new Pin(2, SIDE_S, "A1");
        pins[N_A2] = new Pin(3, SIDE_S, "A2");
        pins[N_A3] = new Pin(4, SIDE_S, "A3");
        pins[N_A4] = new Pin(5, SIDE_S, "A4");
        pins[N_A5] = new Pin(6, SIDE_S, "A5");
        
        // Top - Power
        pins[N_VCC] = new Pin(2, SIDE_N, "5V");
        pins[N_GND] = new Pin(4, SIDE_N, "GND");
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
        vcc = vccVolts - groundVolts;
        
        // Read analog input pins (A0-A5)
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            double voltage = volts[pinIdx] - groundVolts;
            voltage = Math.max(0, Math.min(vcc, voltage)); // Clamp to 0-Vcc
            analogValues[i] = (int)((voltage / vcc) * 1023); // 10-bit ADC
        }
        
        // Execute AVR if running
        if (isRunning && avrRunner != null) {
            double currentTime = sim.t;
            double elapsedTime = currentTime - lastSimTime;
            lastSimTime = currentTime;
            
            // Execute CPU cycles
            double cycles = elapsedTime * CPU_FREQ;
            if (cycles > 0) {
                try {
                    avrRunner.execute(cycles);
                } catch (Exception e) {
                    console("AVR execution error: " + e.getMessage());
                }
            }
            
            // Feed analog values to AVR ADC
            feedAnalogToAVR();
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
    
    // ===== AVR8JS INTEGRATION =====
    
    /**
     * Load Arduino hex file and start AVR emulation
     */
    public void loadHexFile(String hexContent) {
        try {
            console("Loading Arduino hex file...");
            
            // Parse hex file to binary
            Uint8Array program = HexParser.parseHex(hexContent);
            
            // Create AVR runner
            avrRunner = new AVRRunner(program);
            isRunning = true;
            lastSimTime = sim.t;
            
            // Setup UART callback for Serial output
            avrRunner.getUsart().setOnByteTransmit(new AVR8JS.ByteTransmitCallback() {
                public void onByte(int byteValue) {
                    char c = (char) byteValue;
                    serialBuffer.append(c);
                    console("Serial: " + c);
                }
            });
            
            // Setup Port B listener (D8-D13, mapped to bits 0-5 of Port B)
            portBListener = new PortListener() {
                public void onChange(int value, int oldValue) {
                    // Port B bits 0-5 = Arduino D8-D13
                    for (int i = 0; i < 6; i++) {
                        pinStates[8 + i] = ((value >> i) & 1) == 1;
                    }
                }
            };
            avrRunner.getPortB().addListener(portBListener);
            
            // Setup Port C listener (A0-A5, can be used as digital)
            portCListener = new PortListener() {
                public void onChange(int value, int oldValue) {
                    // Port C bits 0-5 = Arduino A0-A5 (pins 14-19)
                    for (int i = 0; i < 6; i++) {
                        pinStates[14 + i] = ((value >> i) & 1) == 1;
                    }
                }
            };
            avrRunner.getPortC().addListener(portCListener);
            
            // Setup Port D listener (D0-D7)
            portDListener = new PortListener() {
                public void onChange(int value, int oldValue) {
                    // Port D = Arduino D0-D7
                    for (int i = 0; i < 8; i++) {
                        pinStates[i] = ((value >> i) & 1) == 1;
                    }
                }
            };
            avrRunner.getPortD().addListener(portDListener);
            
            console("Arduino program loaded successfully!");
            console("AVR is now running at 16MHz");
            
        } catch (Exception e) {
            console("Error loading hex file: " + e.getMessage());
            isRunning = false;
        }
    }
    
    /**
     * Feed analog values from circuit to AVR ADC registers
     */
    private void feedAnalogToAVR() {
        if (avrRunner == null) return;
        
        // TODO: Write analog values to AVR ADC registers
        // This requires writing to specific memory addresses in the AVR
        // For now, the AVR reads whatever is in its ADC registers
    }
    
    /**
     * Stop AVR execution
     */
    public void stopAVR() {
        if (avrRunner != null) {
            try {
                avrRunner.stop();
            } catch (Exception e) {
                console("Error stopping AVR: " + e.getMessage());
            }
        }
        isRunning = false;
        console("AVR stopped");
    }
    
    /**
     * Reset AVR (stop and clear)
     */
    public void resetAVR() {
        stopAVR();
        avrRunner = null;
        serialBuffer.setLength(0);
        for (int i = 0; i < 20; i++) {
            pinStates[i] = false;
        }
        console("AVR reset");
    }
    
    /**
     * Check if AVR is running
     */
    public boolean isRunning() {
        return isRunning && avrRunner != null;
    }
    
    /**
     * Get serial monitor output
     */
    public String getSerialOutput() {
        return serialBuffer.toString();
    }
    
    /**
     * Clear serial buffer
     */
    public void clearSerialOutput() {
        serialBuffer.setLength(0);
    }
    
    /**
     * Console logging
     */
    private native void console(String message) /*-{
        console.log("[Arduino] " + message);
    }-*/;
    
    // ===== UI INTEGRATION =====
    
    @Override
    public void getInfo(String[] arr) {
        arr[0] = "Arduino Uno (ATmega328P)";
        arr[1] = "Status: " + (isRunning ? "Running" : "Stopped");
        arr[2] = "CPU: 16 MHz AVR";
        arr[3] = "VCC = " + getVoltageText(vcc);
        arr[4] = "Serial buffer: " + serialBuffer.length() + " bytes";
        if (isRunning) {
            arr[5] = "Click 'Edit' to view serial monitor";
        } else {
            arr[5] = "Click 'Edit' to load hex file";
        }
    }
    
    @Override
    public EditInfo getEditInfo(int n) {
        if (n == 0) {
            EditInfo ei = new EditInfo("", 0, -1, -1);
            ei.button = new Button("Load Arduino Hex File");
            return ei;
        }
        if (n == 1) {
            EditInfo ei = new EditInfo("", 0, -1, -1);
            ei.button = new Button("View Serial Monitor");
            return ei;
        }
        if (n == 2 && isRunning) {
            EditInfo ei = new EditInfo("", 0, -1, -1);
            ei.button = new Button("Stop AVR");
            return ei;
        }
        if (n == 3 && isRunning) {
            EditInfo ei = new EditInfo("", 0, -1, -1);
            ei.button = new Button("Reset AVR");
            return ei;
        }
        return null;
    }
    
    @Override
    public void setEditValue(int n, EditInfo ei) {
        if (n == 0) {
            new LoadArduinoHexDialog(this);
        }
        if (n == 1) {
            new ArduinoSerialMonitorDialog(this);
        }
        if (n == 2) {
            stopAVR();
        }
        if (n == 3) {
            resetAVR();
        }
    }
    
    int getPostCount() { return 22; }
    int getVoltageSourceCount() { return 0; }
    int getDumpType() { return 400; }
}