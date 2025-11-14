package com.lushprojects.circuitjs1.client;

import com.google.gwt.core.client.JavaScriptObject;
import com.google.gwt.user.client.ui.Button;
import java.util.ArrayList;
import com.google.gwt.user.client.ui.TextArea;

import com.google.gwt.user.client.ui.VerticalPanel;
import com.google.gwt.user.client.ui.Label;
import com.google.gwt.user.client.ui.Button;


/**
 * Arduino Uno element with high-level behavioral simulation
 * Uses JavaScript-based setup/loop code to model Arduino behavior
 * without cycle-accurate AVR emulation.
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

    // Pin state tracking (digital outputs)
    boolean[] pinStates = new boolean[20];
    int[] analogValues = new int[6]; // 10-bit ADC (0-1023)

    // UI / mode options
    int vccChoiceIndex = 0; // 0 = 5V, 1 = 3.3V
    boolean useFixedVcc = false;
    
    // Behavioral mode fields
    private String behavioralId = null;
    private String arduinoSketch = "// Blink Example\nvoid setup() {\n  pinMode(13, OUTPUT);\n}\n\nvoid loop() {\n  digitalWrite(13, HIGH);\n  delay(1000);\n  digitalWrite(13, LOW);\n  delay(1000);\n}";
    private String setupCode = "";
    private String loopCode = "";
    private double[] behavioralPinVoltages = new double[20]; // target voltages from JS
    private int exampleIndex = 0; // 0=Blink, 1=Fade, 2=Button

    // Circuit properties
    int ground;
    double vcc = 5.0;

    public ArduinoElm(int xx, int yy) {
        super(xx, yy);
        for (int i = 0; i < 20; i++) pinStates[i] = false;
        for (int i = 0; i < 6; i++) analogValues[i] = 0;

        vccChoiceIndex = 0;
        useFixedVcc = false;
        transpileArduinoCode();
    }

    String getChipName() { return "Arduino Uno"; }

    void setupPins() {
        sizeX = 7;
        sizeY = 14;
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

        // RIGHT SIDE - Digital pins D13 down to D0
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

    @Override
    public int getPostCount() { return 22; }

    @Override
    public int getVoltageSourceCount() { return 0; }

    void stamp() {
        initBehavioralMode();
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
        double pinResistance = 40;

        // Digital pins D0..D13
        for (int i = 0; i < 14; i++) {
            if (pinStates[i]) {
                pins[i].current = (volts[N_VCC] - volts[i]) / pinResistance;
            } else {
                pins[i].current = (volts[i] - volts[N_GND]) / pinResistance;
            }
            totalCurrent += Math.abs(pins[i].current);
        }

        // Quiescent current
        totalCurrent += 0.05;
        pins[N_VCC].current = -totalCurrent;
        pins[N_GND].current = totalCurrent;
    }

    void startIteration() {
        double groundVolts = volts[N_GND];
        double vccVolts = volts[N_VCC];
        if (useFixedVcc) {
            vcc = (vccChoiceIndex == 0) ? 5.0 : 3.3;
        } else {
            vcc = vccVolts - groundVolts;
        }

        // Read analog inputs
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            double voltage = volts[pinIdx] - groundVolts;
            voltage = Math.max(0, Math.min(vcc, voltage));
            analogValues[i] = (int)((voltage / vcc) * 1023.0);
        }
    }

    @Override
    public void doStep() {
        double pinResistance = 40;
        double highZ = 1e9;

        // Behavioral mode: apply voltages set by JavaScript
        for (int i = 0; i < 14; i++) {
            double targetV = behavioralPinVoltages[i];
            // Drive pin based on target voltage
            if (targetV > vcc * 0.6) {
                // High - connect to VCC through resistance
                sim.stampResistor(nodes[N_VCC], nodes[i], pinResistance);
            } else if (targetV < vcc * 0.4) {
                // Low - connect to ground through resistance
                sim.stampResistor(nodes[i], ground, pinResistance);
            } else {
                // Float/analog - high impedance
                sim.stampResistor(nodes[i], ground, highZ);
            }
        }

        // Analog pins high-Z
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            sim.stampResistor(nodes[pinIdx], ground, highZ);
        }
    }


    
    // Called from JS behavioral MCU to set pin voltage
    public void setBehavioralPinVoltage(int pinIdx, double voltage) {
        if (pinIdx >= 0 && pinIdx < behavioralPinVoltages.length) {
            behavioralPinVoltages[pinIdx] = voltage;
        }
    }
    
    // Get voltage at a specific pin (for JSNI bridge)
    public double getPinVoltage(int pinIdx) {
        if (pinIdx >= 0 && pinIdx < volts.length) {
            return volts[pinIdx];
        }
        return 0.0;
    }


    private void initBehavioralMode() {
        if (behavioralId != null) return;
        try {
            // Register this instance for callbacks
            ArduinoElmBehavioral.setCurrentBehavioralArduino(this);
            
            // Bind circuit adapter on first use
            ArduinoElmBehavioral.jsBindCircuitAdapter();
            
            // Build pin map: nodes for D0-D13, A0-A5
            int[] pinMap = new int[20];
            for (int i = 0; i < 14; i++) pinMap[i] = nodes[i]; // D0-D13
            for (int i = 0; i < 6; i++) pinMap[14 + i] = nodes[N_A0 + i]; // A0-A5
            
            behavioralId = ArduinoElmBehavioral.jsCreateBehavioralMCU(
                pinMap, setupCode, loopCode, 20, 
                "arduino-" + System.identityHashCode(this)
            );
            ArduinoElmBehavioral.jsStartBehavioralMCU(behavioralId);
            CirSim.console("Behavioral MCU started: " + behavioralId);
        } catch (Exception e) {
            CirSim.console("Error initializing behavioral mode: " + e.getMessage());
        }
    }


    // ===== Edit dialog =====
    public EditInfo getEditInfo(int n) {
        if (n == 0) {
            EditInfo ei = new EditInfo("Load Example", exampleIndex, -1, -1);
            ei.choice = new Choice();
            ei.choice.add("Blink (Pin 13)");
            ei.choice.add("Fade (Pin 9)");
            ei.choice.add("Button (Pin 2->13)");
            ei.choice.add("AnalogRead (A0->13)");
            ei.choice.add("Custom");
            ei.choice.select(exampleIndex);
            return ei;
        }
        if (n == 1) {
            EditInfo ei = new EditInfo("VCC selection", vccChoiceIndex, -1, -1);
            ei.choice = new Choice();
            ei.choice.add("5V");
            ei.choice.add("3.3V");
            ei.choice.select(vccChoiceIndex);
            return ei;
        }
        if (n == 2) {
            return EditInfo.createCheckbox("Use fixed VCC", useFixedVcc);
        }
        if (n == 3) {
            TextArea sketchArea = new TextArea();
            sketchArea.setText(arduinoSketch);
            sketchArea.setVisibleLines(20);
            sketchArea.setCharacterWidth(60);
            EditInfo ei = new EditInfo("Arduino Sketch (C++)", 0);
            ei.textArea = sketchArea;
            return ei;
        }

        return null;
    }

    public void setEditValue(int n, EditInfo ei) {
        if (n == 0) {
            int newExample = ei.choice.getSelectedIndex();
            if (newExample != exampleIndex) {
                exampleIndex = newExample;
                loadExample(exampleIndex);
                transpileArduinoCode();
                restartBehavioralMCU();
            }
        } else if (n == 1) {
            vccChoiceIndex = ei.choice.getSelectedIndex();
            if (useFixedVcc) {
                vcc = (vccChoiceIndex == 0) ? 5.0 : 3.3;
            }
        } else if (n == 2) {
            useFixedVcc = ei.checkbox.getState();
            if (useFixedVcc) {
                vcc = (vccChoiceIndex == 0) ? 5.0 : 3.3;
            }
        } else if (n == 3 && ei.textArea != null) {
            arduinoSketch = ei.textArea.getText();
            transpileArduinoCode();
            restartBehavioralMCU();
        }
    }

    private void loadExample(int index) {
        switch(index) {
            case 0: // Blink
                arduinoSketch = "// Blink Example\nvoid setup() {\n  pinMode(13, OUTPUT);\n}\n\nvoid loop() {\n  digitalWrite(13, HIGH);\n  delay(1000);\n  digitalWrite(13, LOW);\n  delay(1000);\n}";
                break;
            case 1: // Fade
                arduinoSketch = "// Fade Example\nint brightness = 0;\nint fadeAmount = 5;\n\nvoid setup() {\n  pinMode(9, OUTPUT);\n}\n\nvoid loop() {\n  analogWrite(9, brightness);\n  brightness += fadeAmount;\n  if (brightness <= 0 || brightness >= 255) {\n    fadeAmount = -fadeAmount;\n  }\n  delay(30);\n}";
                break;
            case 2: // Button
                arduinoSketch = "// Button Example\nint buttonPin = 2;\nint ledPin = 13;\n\nvoid setup() {\n  pinMode(ledPin, OUTPUT);\n  pinMode(buttonPin, INPUT);\n}\n\nvoid loop() {\n  int buttonState = digitalRead(buttonPin);\n  digitalWrite(ledPin, buttonState);\n}";
                break;
            case 3: // AnalogRead
                arduinoSketch = "// AnalogRead Example\nint sensorPin = A0;\nint ledPin = 13;\n\nvoid setup() {\n  pinMode(ledPin, OUTPUT);\n}\n\nvoid loop() {\n  int sensorValue = analogRead(sensorPin);\n  if (sensorValue > 512) {\n    digitalWrite(ledPin, HIGH);\n  } else {\n    digitalWrite(ledPin, LOW);\n  }\n  delay(100);\n}";
                break;
        }
    }
    
    private void transpileArduinoCode() {
        String[] result = ArduinoElmBehavioral.transpileArduinoToJS(arduinoSketch);
        setupCode = result[0];
        loopCode = result[1];
        
        // Log transpiled code for debugging
        CirSim.console("=== Arduino Sketch Transpiled ===");
        CirSim.console("Setup JS: " + setupCode);
        CirSim.console("Loop JS: " + loopCode);
    }
    
    private void restartBehavioralMCU() {
        if (behavioralId != null) {
            ArduinoElmBehavioral.jsDestroyBehavioralMCU(behavioralId);
            behavioralId = null;
        }
        initBehavioralMode();
    }

    @Override
    public void getInfo(String[] arr) {
        arr[0] = "Arduino Uno (High-Level Simulation)";
        String mode = useFixedVcc ? (vccChoiceIndex == 0 ? " (fixed 5V)" : " (fixed 3.3V)") : " (from circuit)";
        arr[1] = "VCC = " + getVoltageText(vcc) + mode;
        arr[2] = "Setup/Loop: JavaScript-based behavior";
    }

    int getDumpType() { return 400; }
}
