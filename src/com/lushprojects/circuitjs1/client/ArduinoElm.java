package com.lushprojects.circuitjs1.client;

import com.google.gwt.user.client.ui.TextArea;
import java.util.ArrayList;

/**
 * Updated ArduinoElm that integrates a Java-side ArduinoRuntime.
 * - Removes JS behavioral dependency
 * - Adds runtime integration
 * - Keeps original pin mapping & UI
 */
class ArduinoElm extends ChipElm {
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

    // pins state
    boolean[] pinStates = new boolean[20];      // logical HIGH/LOW (for convenience)
    int[] analogValues = new int[6];            // A0..A5 0..1023

    // hardware model
    private double[] desiredVoltages = new double[20]; // desired output voltages from runtime (V)
    private int[] pinMode = new int[20]; // 0 = INPUT, 1 = OUTPUT, 2 = INPUT_PULLUP

    int vccChoiceIndex = 0;
    boolean useFixedVcc = false;

    private String arduinoSketch = "// Blink Example\nvoid setup() {\n  pinMode(13, OUTPUT);\n}\n\nvoid loop() {\n  digitalWrite(13, HIGH);\n  delay(1000);\n  digitalWrite(13, LOW);\n  delay(1000);\n}";
    private String setupCode = "";
    private String loopCode = "";
    private int exampleIndex = 0;

    int ground;
    double vcc = 5.0;

    // The new runtime (the Arduino "brain")
    private ArduinoRuntime runtime;

    public ArduinoElm(int xx, int yy) {
        super(xx, yy);
        for (int i = 0; i < 20; i++) {
            pinStates[i] = false;
            desiredVoltages[i] = 0.0;
            pinMode[i] = 0; // default INPUT
        }
        for (int i = 0; i < 6; i++) analogValues[i] = 0;

        vccChoiceIndex = 0;
        useFixedVcc = false;

        // create runtime and load simple example IR
        runtime = new ArduinoRuntime(this);
        runtime.loadExample(exampleIndex); // loads builtin example like Blink
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
        // still stamp nonlinear for each pin so solver handles it
        ground = nodes[N_GND];

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

        // Advance runtime: 1 ms per doStep
        runtime.advanceTimeMillis(1);
        runtime.step(50); // run up to 50 instructions per simulator step

        // Use desiredVoltages & pinMode to stamp resistors to VCC or GND
        for (int i = 0; i < 14; i++) { // only digital pins D0..D13
            double targetV = desiredVoltages[i];
            if (pinMode[i] == ArduinoRuntime.PINMODE_OUTPUT) {
                // Output: drive toward target voltage through a small series (pinResistance)
                if (targetV > vcc * 0.6) {
                    // HIGH
                    sim.stampResistor(nodes[N_VCC], nodes[i], pinResistance);
                } else if (targetV < vcc * 0.4) {
                    // LOW
                    sim.stampResistor(nodes[i], ground, pinResistance);
                } else {
                    // if target is analog mid-level, drive with a resistor to that voltage approximated by dividing
                    // simpler: stamp a resistor to ground and VCC ratio (skip complexity for now)
                    sim.stampResistor(nodes[i], ground, highZ);
                }
            } else if (pinMode[i] == ArduinoRuntime.PINMODE_INPUT_PULLUP) {
                // weak pull-up to VCC
                sim.stampResistor(nodes[N_VCC], nodes[i], 10000.0); // 10k pull-up
            } else { // INPUT
                sim.stampResistor(nodes[i], ground, highZ);
            }
        }

        // Analog pins: let circuit set them (high impedance) unless the runtime uses analogWrite (PWM)
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            sim.stampResistor(nodes[pinIdx], ground, highZ);
        }
    }

   
    private void compileAndLoadCustomSketch() {
        try {
            // 1. Parse
            AST.Program prog = ArduinoParser.parseProgram(arduinoSketch);

            // 2. Compile
            ArduinoCompiler.CompileResult res = ArduinoCompiler.compile(prog);

            // 3. Load into runtime
            runtime.setupInstrs.clear();
            runtime.loopInstrs.clear();
            runtime.setupInstrs.addAll(res.setup);
            runtime.loopInstrs.addAll(res.loop);

            // 4. Reset runtime
            runtime.pc = 0;
            runtime.setupDone = false;

            CirSim.console("Custom sketch compiled & loaded successfully.");
        }
        catch (Exception e) {
            CirSim.console("Error compiling sketch: " + e.getMessage());
        }
    }


    // Methods used by the runtime to interact with hardware ----------------

    /**
     * Read the instantaneous voltage on the Arduino pin (volts[] is maintained by CirSim).
     * @param arduinoPin a logical pin number 0..19 (D0..D13, A0..A5)
     * @return voltage measured relative to ground
     */
    public double readPinVoltage(int arduinoPin) {
        if (arduinoPin < 0 || arduinoPin >= 20) return 0.0;
        int nodeIndex = (arduinoPin < 14) ? arduinoPin : (N_A0 + (arduinoPin - 14));
        // volts[] is available in ChipElm
        return volts[nodeIndex];
    }

    /**
     * Request the hardware to drive a pin to a desired voltage. The actual stamping happens
     * during doStep() so the circuit solver resolves currents accordingly.
     * @param arduinoPin 0..19
     * @param voltage volts (0..vcc)
     */
    public void writePinVoltage(int arduinoPin, double voltage) {
        if (arduinoPin < 0 || arduinoPin >= 20) return;
        desiredVoltages[arduinoPin] = voltage;
        // for convenience also set logical state
        pinStates[arduinoPin] = voltage > (vcc * 0.6);
    }

    /**
     * Set pin mode: 0 INPUT, 1 OUTPUT, 2 INPUT_PULLUP
     */
    public void setPinMode(int arduinoPin, int mode) {
        if (arduinoPin < 0 || arduinoPin >= 20) return;
        pinMode[arduinoPin] = mode;
    }

    /**
     * Return the analog value (0..1023) sampled by startIteration
     */
    public int getAnalogValue(int analogIndex) {
        if (analogIndex < 0 || analogIndex >= 6) return 0;
        return analogValues[analogIndex];
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
            ei.choice.add("Custom Sketch");
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
                if (exampleIndex == 4) { // assuming “Custom Sketch” is index 4
                    compileAndLoadCustomSketch();
                } else {
                    runtime.loadExample(exampleIndex);
                }
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
             if (exampleIndex == 4) { // custom sketch selected
                compileAndLoadCustomSketch();
             }
            // For now we do not parse C++; you can later add parser to convert to IR and load it.
            // To avoid surprising behavior, we keep UI editable but do not auto-transpile here.
        }
    }

    @Override
    public void getInfo(String[] arr) {
        arr[0] = "Arduino Uno (High-Level Simulation)";
        String mode = useFixedVcc ? (vccChoiceIndex == 0 ? " (fixed 5V)" : " (fixed 3.3V)") : " (from circuit)";
        arr[1] = "VCC = " + getVoltageText(vcc) + mode;
        arr[2] = "Setup/Loop: Java runtime behavior";
    }

    int getDumpType() { return 400; }
}
