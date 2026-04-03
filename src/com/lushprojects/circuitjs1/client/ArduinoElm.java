package com.lushprojects.circuitjs1.client;

import com.google.gwt.core.client.Callback;
import com.google.gwt.core.client.ScriptInjector;
import com.google.gwt.user.client.ui.TextArea;

/**
 * ArduinoElm - Arduino Uno simulation using avr8js (real AVR execution).
 *
 * Integration:
 *  1. avr8js.bundle.js is loaded once from war/avr8js/ via ScriptInjector.
 *  2. On edit dialog OK, jsInitSimulator() POSTs the sketch to
 *     hexi.wokwi.com/build, receives Intel HEX, parses it and boots an
 *     avr8js CPU - all happening in JavaScript via JSNI.
 *  3. Every doStep() calls jsRunCycles(500) to advance the AVR simulation,
 *     then jsReadPinStates() to pull D0-D13 state back into Java.
 *  4. startIteration() converts circuit node voltages to ADC counts and
 *     writes them into the AVR data memory so analogRead() works.
 *
 * Node/post mapping:
 *   nodes[0..13]  = D0..D13   (digital pins)
 *   nodes[14..19] = A0..A5    (analog pins)
 *   nodes[20]     = VCC
 *   nodes[21]     = GND
 */
class ArduinoElm extends ChipElm {

    // node index constants
    static final int N_D0  = 0,  N_D1  = 1,  N_D2  = 2,  N_D3  = 3;
    static final int N_D4  = 4,  N_D5  = 5,  N_D6  = 6,  N_D7  = 7;
    static final int N_D8  = 8,  N_D9  = 9,  N_D10 = 10, N_D11 = 11;
    static final int N_D12 = 12, N_D13 = 13;
    static final int N_A0  = 14, N_A1  = 15, N_A2  = 16;
    static final int N_A3  = 17, N_A4  = 18, N_A5  = 19;
    static final int N_VCC = 20, N_GND = 21;

    static final double PIN_R  = 40.0;   // AVR output impedance ~40 ohms
    static final double HIGH_Z = 1.0e9;  // high-impedance for input pins

    // Runtime pin state - NOT final so JSNI can write to the backing array
    boolean[] pinHigh   = new boolean[20]; // true = AVR driving HIGH
    boolean[] pinOutput = new boolean[20]; // true = pin is OUTPUT mode

    private double  vcc       = 5.0;
    private int     vccChoice = 0;      // 0=5V, 1=3.3V
    private boolean fixedVcc  = false;

    private int    exampleIndex  = 0;
    private String arduinoSketch = EXAMPLE_CODE[0];

    // shared across all instances - only load the bundle once
    private static boolean avr8jsLoaded  = false;
    private static boolean avr8jsLoading = false;

    static final String[] EXAMPLE_NAMES = {
        "Blink (Pin 13)",
        "Fade (Pin 9)",
        "Button (Pin 2 -> 13)",
        "AnalogRead (A0 -> 13)",
        "Custom Sketch"
    };

    static final String[] EXAMPLE_CODE = {
        // 0 Blink
        "void setup() {\n  pinMode(13, OUTPUT);\n}\nvoid loop() {\n  digitalWrite(13, HIGH);\n  delay(1000);\n  digitalWrite(13, LOW);\n  delay(1000);\n}",
        // 1 Fade
        "int brightness = 0;\nint fadeAmount = 5;\nvoid setup() {\n  pinMode(9, OUTPUT);\n}\nvoid loop() {\n  analogWrite(9, brightness);\n  brightness += fadeAmount;\n  if (brightness == 0 || brightness == 255) fadeAmount = -fadeAmount;\n  delay(30);\n}",
        // 2 Button
        "void setup() {\n  pinMode(2, INPUT_PULLUP);\n  pinMode(13, OUTPUT);\n}\nvoid loop() {\n  digitalWrite(13, !digitalRead(2));\n}",
        // 3 AnalogRead
        "void setup() {\n  pinMode(13, OUTPUT);\n}\nvoid loop() {\n  int val = analogRead(A0);\n  digitalWrite(13, val > 512);\n  delay(100);\n}",
        // 4 Custom placeholder
        "void setup() {\n\n}\nvoid loop() {\n\n}"
    };

    // constructors

    public ArduinoElm(int xx, int yy) {
        super(xx, yy);
        ensureAvr8jsLoaded();
    }

    public ArduinoElm(int xa, int ya, int xb, int yb, int f,
                      StringTokenizer st) {
        super(xa, ya, xb, yb, f, st);
        try { exampleIndex = Integer.parseInt(st.nextToken()); }
        catch (Exception e) {}
        try { vccChoice = Integer.parseInt(st.nextToken()); }
        catch (Exception e) {}
        try { fixedVcc = Boolean.parseBoolean(st.nextToken()); }
        catch (Exception e) {}
        try {
            StringBuilder sb = new StringBuilder();
            while (st.hasMoreTokens()) {
                if (sb.length() > 0) sb.append(' ');
                sb.append(st.nextToken());
            }
            String loaded = sb.toString().trim();
            if (!loaded.isEmpty())
                arduinoSketch = loaded.replace("\\n", "\n");
        } catch (Exception e) {}
        ensureAvr8jsLoaded();
    }

    // avr8js loader

    private void ensureAvr8jsLoaded() {
        if (avr8jsLoaded || avr8jsLoading) {
            // already loaded from a previous instance - compile immediately
            if (avr8jsLoaded) jsInitSimulator(arduinoSketch);
            return;
        }
        avr8jsLoading = true;
        final ArduinoElm self = this;
        ScriptInjector
            .fromUrl("avr8js/avr8js.bundle.js")
            .setWindow(ScriptInjector.TOP_WINDOW)
            .setCallback(new Callback<Void, Exception>() {
                public void onSuccess(Void result) {
                    avr8jsLoaded  = true;
                    avr8jsLoading = false;
                    CirSim.console("[ArduinoElm] avr8js bundle loaded.");
                    self.jsInitSimulator(self.arduinoSketch);
                }
                public void onFailure(Exception reason) {
                    avr8jsLoading = false;
                    CirSim.console("[ArduinoElm] Failed to load avr8js: "
                                   + reason.getMessage());
                }
            })
            .inject();
    }

    // ChipElm overrides

    String  getChipName()           { return "Arduino Uno"; }
    boolean nonLinear()             { return true; }
    boolean isDigitalChip()         { return false; }
    public int getPostCount()          { return 22; }
    public int getVoltageSourceCount() { return 0; }

    void setupPins() {
        sizeX = 7;
        sizeY = 14;
        pins  = new Pin[22];

        pins[N_VCC] = new Pin(3, SIDE_N, "5V");
        pins[N_GND] = new Pin(3, SIDE_S, "GND");

        pins[N_A0] = new Pin(6,  SIDE_W, "A0");
        pins[N_A1] = new Pin(7,  SIDE_W, "A1");
        pins[N_A2] = new Pin(8,  SIDE_W, "A2");
        pins[N_A3] = new Pin(9,  SIDE_W, "A3");
        pins[N_A4] = new Pin(10, SIDE_W, "A4");
        pins[N_A5] = new Pin(11, SIDE_W, "A5");

        pins[N_D13] = new Pin(0,  SIDE_E, "13");
        pins[N_D12] = new Pin(1,  SIDE_E, "12");
        pins[N_D11] = new Pin(2,  SIDE_E, "~11");
        pins[N_D10] = new Pin(3,  SIDE_E, "~10");
        pins[N_D9]  = new Pin(4,  SIDE_E, "~9");
        pins[N_D8]  = new Pin(5,  SIDE_E, "8");
        pins[N_D7]  = new Pin(6,  SIDE_E, "7");
        pins[N_D6]  = new Pin(7,  SIDE_E, "~6");
        pins[N_D5]  = new Pin(8,  SIDE_E, "~5");
        pins[N_D4]  = new Pin(9,  SIDE_E, "4");
        pins[N_D3]  = new Pin(10, SIDE_E, "~3");
        pins[N_D2]  = new Pin(11, SIDE_E, "2");
        pins[N_D1]  = new Pin(12, SIDE_E, "TX");
        pins[N_D0]  = new Pin(13, SIDE_E, "RX");
    }

    // circuit matrix

    void stamp() {
        for (int i = 0; i < 22; i++)
            sim.stampNonLinear(nodes[i]);
    }

    void startIteration() {
        if (fixedVcc) {
            vcc = (vccChoice == 0) ? 5.0 : 3.3;
        } else {
            vcc = volts[N_VCC] - volts[N_GND];
            if (vcc < 1.8) vcc = 1.8;
            if (vcc > 5.5) vcc = 5.5;
        }

        // Push analog pin voltages into AVR ADC registers
        if (avr8jsLoaded) {
            for (int ch = 0; ch < 6; ch++) {
                double v = volts[N_A0 + ch] - volts[N_GND];
                v = Math.max(0.0, Math.min(vcc, v));
                int adcVal = (int) ((v / vcc) * 1023.0);
                jsSetAnalogInput(ch, adcVal);
            }
        }
    }

    public void doStep() {
        if (avr8jsLoaded && jsIsSimReady()) {
            jsRunCycles(500);   // ~31 us of AVR time at 16 MHz
            jsReadPinStates();
        }

        // Stamp digital pins D0..D13
        for (int i = 0; i < 14; i++) {
            if (pinOutput[i]) {
                if (pinHigh[i])
                    sim.stampResistor(nodes[N_VCC], nodes[i], PIN_R);
                else
                    sim.stampResistor(nodes[i], nodes[N_GND], PIN_R);
            } else {
                sim.stampResistor(nodes[i], nodes[N_GND], HIGH_Z);
            }
        }

        // Analog pins are always high-impedance inputs
        for (int i = 0; i < 6; i++)
            sim.stampResistor(nodes[N_A0 + i], nodes[N_GND], HIGH_Z);
    }

    void calculateCurrent() {
        double total = 0.0;
        for (int i = 0; i < 14; i++) {
            if (pinOutput[i]) {
                pins[i].current = pinHigh[i]
                    ? (volts[N_VCC] - volts[i]) / PIN_R
                    : (volts[i] - volts[N_GND]) / PIN_R;
            } else {
                pins[i].current = 0.0;
            }
            total += Math.abs(pins[i].current);
        }
        for (int i = 0; i < 6; i++) pins[N_A0 + i].current = 0.0;
        pins[N_VCC].current = -(total + 0.05); // 50 mA quiescent
        pins[N_GND].current =  (total + 0.05);
    }

    // JSNI bridge methods

    private native void jsInitSimulator(String sketch) /*-{
        var AVR = $wnd.AVR8JS;
        if (!AVR) {
            console.error("[ArduinoElm] AVR8JS global not found");
            return;
        }

        $wnd._avr8 = null;

        fetch("https://hexi.wokwi.com/build", {
            method  : "POST",
            headers : { "Content-Type": "application/json" },
            body    : JSON.stringify({ sketch: sketch })
        })
        .then(function(r) {
            if (!r.ok) {
            throw "HTTP error " + r.status;
            }
            return r.json();
        })
        .then(function(result) {
            if (!result.hex) {
                console.error("[ArduinoElm] Compile error:\n" + result.stderr);
                return;
            }

            var progBytes = AVR.parseHex(result.hex);
            var cpu = new AVR.CPU(new Uint16Array(progBytes.buffer));

            // Timers power delay() / millis() / PWM
            var timer0 = new AVR.AVRTimer(cpu, AVR.timer0Config);
            var timer1 = new AVR.AVRTimer(cpu, AVR.timer1Config);
            var timer2 = new AVR.AVRTimer(cpu, AVR.timer2Config);

            // GPIO ports
            var portD = new AVR.AVRIOPort(cpu, AVR.portDConfig); // D0-D7
            var portB = new AVR.AVRIOPort(cpu, AVR.portBConfig); // D8-D13
            var portC = new AVR.AVRIOPort(cpu, AVR.portCConfig); // A0-A5

            var pinHigh   = [];
            var pinOutput = [];

            for (var i = 0; i < 14; i++) {
                pinHigh[i]   = false;
                pinOutput[i] = false;
            }
            
            function syncPort(port, base, count) {
                for (var p = 0; p < count; p++) {
                    var s = port.pinState(p);
                    pinHigh  [base + p] = (s === AVR.PinState.High);
                    pinOutput[base + p] = (s !== AVR.PinState.Input &&
                                           s !== AVR.PinState.InputPullUp);
                }
            }

            portD.addListener(function() { syncPort(portD, 0, 8); });
            portB.addListener(function() { syncPort(portB, 8, 6); });

            $wnd._avr8 = {
                cpu: cpu,
                portB: portB, portC: portC, portD: portD,
                timer0: timer0, timer1: timer1, timer2: timer2,
                pinHigh: pinHigh, pinOutput: pinOutput
            };
            console.log("[ArduinoElm] Simulator ready.");
        }, function(e) {
        console.error("[ArduinoElm] hexi error: " + e);
    });
    }-*/;

    private native boolean jsIsSimReady() /*-{
        return !!($wnd._avr8 && $wnd._avr8.cpu);
    }-*/;

    private native void jsRunCycles(int cycles) /*-{
        var sim = $wnd._avr8;
        if (!sim) return;
        var exec = $wnd.AVR8JS.avrInstruction;
        var cpu  = sim.cpu;
        for (var i = 0; i < cycles; i++) {
            exec(cpu);
            cpu.tick();
        }
    }-*/;

    private native void jsReadPinStates() /*-{
        var sim = $wnd._avr8;
        if (!sim) return;
        var jH = this.@com.lushprojects.circuitjs1.client.ArduinoElm::pinHigh;
        var jO = this.@com.lushprojects.circuitjs1.client.ArduinoElm::pinOutput;
        var ph = sim.pinHigh;
        var po = sim.pinOutput;
        for (var i = 0; i < 14; i++) {
            jH[i] = ph[i] ? true : false;
            jO[i] = po[i] ? true : false;
        }
    }-*/;

    private native void jsSetAnalogInput(int channel, int adcVal) /*-{
        var sim = $wnd._avr8;
        if (!sim) return;
        var data  = sim.cpu.data;
        var admux = data[0x7C] & 0x0F; // currently selected ADC channel
        if (admux === channel) {
            data[0x78] = adcVal & 0xFF;         // ADCL
            data[0x79] = (adcVal >> 8) & 0x03;  // ADCH
            data[0x7A] = data[0x7A] | 0x10;     // ADCSRA: set ADIF (conversion done)
        }
    }-*/;

    // edit dialog

    public EditInfo getEditInfo(int n) {
        switch (n) {
            case 0: {
                EditInfo ei = new EditInfo("Load Example", exampleIndex, -1, -1);
                ei.choice = new Choice();
                for (int i = 0; i < EXAMPLE_NAMES.length; i++)
                    ei.choice.add(EXAMPLE_NAMES[i]);
                ei.choice.select(exampleIndex);
                return ei;
            }
            case 1: {
                EditInfo ei = new EditInfo("VCC selection", vccChoice, -1, -1);
                ei.choice = new Choice();
                ei.choice.add("5V");
                ei.choice.add("3.3V");
                ei.choice.select(vccChoice);
                return ei;
            }
            case 2:
                return EditInfo.createCheckbox("Use fixed VCC", fixedVcc);
            case 3: {
                TextArea ta = new TextArea();
                ta.setText(arduinoSketch);
                ta.setVisibleLines(20);
                ta.setCharacterWidth(60);
                EditInfo ei = new EditInfo("Arduino Sketch (C++)", 0);
                ei.textArea = ta;
                return ei;
            }
            default: return null;
        }
    }

    public void setEditValue(int n, EditInfo ei) {
        switch (n) {
            case 0:
                int newIdx = ei.choice.getSelectedIndex();
                if (newIdx != exampleIndex) {
                    exampleIndex  = newIdx;
                    arduinoSketch = EXAMPLE_CODE[exampleIndex];
                }
                if (avr8jsLoaded) jsInitSimulator(arduinoSketch);
                break;
            case 1:
                vccChoice = ei.choice.getSelectedIndex();
                if (fixedVcc) vcc = (vccChoice == 0) ? 5.0 : 3.3;
                break;
            case 2:
                fixedVcc = ei.checkbox.getState();
                if (fixedVcc) vcc = (vccChoice == 0) ? 5.0 : 3.3;
                break;
            case 3:
                if (ei.textArea != null) {
                    arduinoSketch = ei.textArea.getText();
                    if (avr8jsLoaded)
                        jsInitSimulator(arduinoSketch);
                    else
                        CirSim.console("[ArduinoElm] avr8js not ready yet.");
                }
                break;
        }
    }

    // info panel

    public void getInfo(String[] arr) {
        arr[0] = "Arduino Uno (avr8js)";
        arr[1] = "VCC = " + getVoltageText(vcc)
                 + (fixedVcc ? " (fixed)" : " (from circuit)");
        if (!avr8jsLoaded)
            arr[2] = "Loading avr8js...";
        else if (!jsIsSimReady())
            arr[2] = "Ready - double-click to compile";
        else
            arr[2] = "Running";
    }

    // serialisation

    public String dump() {
        String enc = arduinoSketch
            .replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("\r", "");
        return super.dump()
               + " " + exampleIndex
               + " " + vccChoice
               + " " + fixedVcc
               + " " + enc;
    }

    int getDumpType() { return 400; }
}
