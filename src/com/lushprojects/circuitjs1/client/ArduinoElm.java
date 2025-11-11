package com.lushprojects.circuitjs1.client;

import com.google.gwt.core.client.JavaScriptObject;
import com.google.gwt.user.client.ui.Button;
import java.util.ArrayList;
import com.google.gwt.user.client.ui.TextArea;

/**
 * Arduino Uno element with AVR8JS emulation (GWT JSNI bridge)
 * Runs real Arduino code compiled to Intel HEX files.
 *
 * Notes:
 * - Ensure avr8js.umd.js and avr-bridge.js are loaded before circuitjs1.nocache.js
 * - avr-bridge.js must expose window.AVRBridge with proper API
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
    boolean serialEnabled = true;

    // Serial output buffer
    private StringBuilder serialBuffer = new StringBuilder();

    // Circuit properties
    int ground;
    double vcc = 5.0;
    TextArea code = new TextArea();

    // AVR/GWT bridge
    private JavaScriptObject avr = null;
    private double clockHz = 16_000_000;
    private double cycleAcc = 0.0;
    private String loadedHexText = null;

    // Cached port values
    private int portBValue = 0;
    private int portCValue = 0;
    private int portDValue = 0;

    public ArduinoElm(int xx, int yy) {
        super(xx, yy);
        for (int i = 0; i < 20; i++) pinStates[i] = false;
        for (int i = 0; i < 6; i++) analogValues[i] = 0;

        vccChoiceIndex = 0;
        useFixedVcc = false;
        serialEnabled = true;
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
        initAvrIfNeeded();
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

        // Run AVR cycles
        double dt = sim.timeStep;
        cycleAcc += clockHz * dt;
        int run = (int) Math.floor(cycleAcc);
        if (run > 0 && avr != null) {
            cycleAcc -= run;
            avrStep(avr, run);
        }

        // Stamp digital pins
        for (int i = 0; i < 14; i++) {
            if (pinStates[i]) {
                sim.stampResistor(nodes[N_VCC], nodes[i], pinResistance);
            } else {
                sim.stampResistor(nodes[i], ground, pinResistance);
            }
        }

        // Analog pins high-Z
        for (int i = 0; i < 6; i++) {
            int pinIdx = N_A0 + i;
            sim.stampResistor(nodes[pinIdx], ground, highZ);
        }

        // Sample digital inputs
        for (int pd = 0; pd <= 7; pd++) {
            int pinIndex = pd;
            double vin = volts[pinIndex];
            boolean high = vin > (0.6 * vcc);
            if (avr != null) {
                avrSetInputBit(avr, "D", pd, high);
            }
        }
    }

    // ===== JSNI: Bridge to AVRBridge =====
    private static native JavaScriptObject avrCreate(double clockHz) /*-{
      try {
        if (!$wnd.AVRBridge || !$wnd.AVRBridge.create) {
          console.error("AVRBridge not found. Ensure avr-bridge.js is loaded.");
          return null;
        }
        return $wnd.AVRBridge.create({ clockHz: clockHz });
      } catch (e) {
        console.error("avrCreate error:", e);
        return null;
      }
    }-*/;

    private static native void avrLoadHex(JavaScriptObject avr, String hex) /*-{
      if (!avr || !avr.loadHex) {
        console.error("AVR instance or loadHex method not available");
        return;
      }
      try {
        avr.loadHex(hex);
      } catch (e) {
        console.error("avrLoadHex error:", e);
      }
    }-*/;

    private static native void avrStep(JavaScriptObject avr, int cycles) /*-{
      if (!avr || !avr.step) return;
      try {
        avr.step(cycles);
      } catch (e) {
        console.error("avrStep error:", e);
      }
    }-*/;

    private static native void avrSetCallbacks(JavaScriptObject avr, ArduinoElm self) /*-{
      if (!avr || !avr.setCallbacks) {
        console.error("AVR instance or setCallbacks method not available");
        return;
      }
      try {
        avr.setCallbacks({
          onPortBWrite: $entry(function (v) {
            self.@com.lushprojects.circuitjs1.client.ArduinoElm::onPortBWrite(I)(v);
          }),
          onPortCWrite: $entry(function (v) {
            self.@com.lushprojects.circuitjs1.client.ArduinoElm::onPortCWrite(I)(v);
          }),
          onPortDWrite: $entry(function (v) {
            self.@com.lushprojects.circuitjs1.client.ArduinoElm::onPortDWrite(I)(v);
          }),
          onUsartTx: $entry(function (b) {
            self.@com.lushprojects.circuitjs1.client.ArduinoElm::onUsartTx(I)(b);
          }),
          onAdcRead: $entry(function (ch) {
            return self.@com.lushprojects.circuitjs1.client.ArduinoElm::onAdcRead(I)(ch);
          })
        });
      } catch (e) {
        console.error("avrSetCallbacks error:", e);
      }
    }-*/;

    private static native void avrSetInputBit(JavaScriptObject avr, String port, int bit, boolean high) /*-{
      if (!avr || !avr.setInputBit) return;
      try {
        avr.setInputBit(port, bit, high);
      } catch (e) {
        console.error("avrSetInputBit error:", e);
      }
    }-*/;

    private void initAvrIfNeeded() {
        if (avr != null) return;
        
        try {
            avr = avrCreate(clockHz);
            if (avr == null) {
                CirSim.console("Failed to create AVR instance - check console");
                return;
            }
            
            avrSetCallbacks(avr, this);

            String hex = (this.loadedHexText != null && this.loadedHexText.length() > 0)
                    ? this.loadedHexText
                    : ":020000040000FA\n:00000001FF"; // minimal placeholder
            avrLoadHex(avr, hex);
        } catch (Exception e) {
            CirSim.console("Error initializing AVR: " + e.getMessage());
        }
    }

    // ===== Callbacks from JavaScript =====
    private void onPortBWrite(int value) {
        portBValue = value & 0xFF;
        for (int bit = 0; bit <= 5; bit++) {
            int digitalPin = N_D8 + bit;
            if (digitalPin < pinStates.length) {
                pinStates[digitalPin] = ((portBValue >> bit) & 1) != 0;
            }
        }
    }

    private void onPortCWrite(int value) {
        portCValue = value & 0xFF;
    }

    private void onPortDWrite(int value) {
        portDValue = value & 0xFF;
        for (int bit = 0; bit <= 7; bit++) {
            int digitalPin = N_D0 + bit;
            if (digitalPin < pinStates.length) {
                pinStates[digitalPin] = ((portDValue >> bit) & 1) != 0;
            }
        }
    }

    private void onUsartTx(int byteVal) {
        if (serialEnabled) {
            serialBuffer.append((char)(byteVal & 0xFF));
            if (serialBuffer.length() > 4096) {
                serialBuffer.delete(0, serialBuffer.length() - 4096);
            }
        }
    }

    private int onAdcRead(int channel) {
        if (channel < 0 || channel > 5) return 0;
        
        int pinIndex = N_A0 + channel;
        double v = volts[pinIndex];
        double groundVolts = volts[N_GND];
        double valueV = Math.max(0, Math.min(v - groundVolts, vcc));
        int adc = (int)Math.round(1023.0 * (valueV / vcc));
        return adc & 0x3FF;
    }

    public void setFirmwareHex(String hex) {
        this.loadedHexText = hex;
        if (avr != null && hex != null && hex.length() > 0) {
            avrLoadHex(avr, hex);
        }
    }

    // ===== Edit dialog =====
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
        if (n == 3) {
            return new EditInfo("Code: ", code).
                    setDimensionless();
        }
        return null;
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
            if (!serialEnabled) serialBuffer.setLength(0);
        }
    }

    @Override
    public void getInfo(String[] arr) {
        arr[0] = "Arduino Uno (ATmega328P)";
        arr[1] = "CPU: 16 MHz AVR";
        String mode = useFixedVcc ? (vccChoiceIndex == 0 ? " (fixed 5V)" : " (fixed 3.3V)") : " (from circuit)";
        arr[2] = "VCC = " + getVoltageText(vcc) + mode;
        arr[3] = "Serial: " + (serialEnabled ? "enabled" : "disabled") + ", buffer=" + serialBuffer.length() + " bytes";
    }

    int getDumpType() { return 400; }
}
