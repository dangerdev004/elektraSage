package com.lushprojects.circuitjs1.client;

import java.util.ArrayList;
import java.util.List;

/**
 * Minimal Arduino runtime / interpreter.
 *
 * Execution model:
 * - setupInstrs: executed once at reset
 * - loopInstrs: executed repeatedly; when pc reaches end it wraps to 0
 *
 * Instructions implement Instr.execute(rt) and return true if the instruction
 * completed (pc should advance). Delay keeps returning false until target time reached.
 *
 * Time model:
 * - runtimeMillis is advanced by ArduinoElm.doStep() via advanceTimeMillis(ms)
 *
 * This runtime is intentionally small — add features (reads, conditionals, functions)
 * by extending Instr classes in Instr.java.
 */
public class ArduinoRuntime {

    public static final int PINMODE_INPUT = 0;
    public static final int PINMODE_OUTPUT = 1;
    public static final int PINMODE_INPUT_PULLUP = 2;

    final ArduinoElm hw;

    long runtimeMillis = 0L;

    List<Instr> setupInstrs = new ArrayList<>();
    List<Instr> loopInstrs = new ArrayList<>();

    // program counters
    int pc = 0;
    boolean setupDone = false;

    public ArduinoRuntime(ArduinoElm hw) {
        this.hw = hw;
    }

    /**
     * Advance logical time by ms milliseconds.
     */
    public void advanceTimeMillis(long ms) {
        if (ms <= 0) return;
        runtimeMillis += ms;
    }

    /**
     * Run up to maxInstructions. If an instruction blocks (e.g. Delay), it will be re-attempted
     * on the next step call (non-blocking to circuit solver).
     */
    public void step(int maxInstructions) {
        int executed = 0;

        // First run setup if needed
        if (!setupDone) {
            for (int i = 0; i < setupInstrs.size(); ) {
                Instr ins = setupInstrs.get(i);
                boolean done = ins.execute(this);
                if (done) {
                    i++;
                } else {
                    // instruction blocked (likely delay); return to allow solver tick
                    return;
                }
                executed++;
                if (executed >= maxInstructions) return;
            }
            setupDone = true;
            // reset pc for loop
            pc = 0;
        }

        // run loop instructions
        while (executed < maxInstructions && loopInstrs.size() > 0) {
            if (pc >= loopInstrs.size()) pc = 0;
            Instr ins = loopInstrs.get(pc);
            boolean done = ins.execute(this);
            if (done) {
                pc++;
            } else {
                // blocked (e.g. delay) - do not advance pc, return and retry later
                return;
            }
            executed++;
        }
    }

    public long millis() {
        return runtimeMillis;
    }

    // ---- convenience helpers used by Instr implementations ----
    public void digitalWrite(int pin, boolean value) {
        double v = value ? hw.vcc : 0.0;
        hw.writePinVoltage(pin, v);
        // Also set pin mode output if not already
        hw.setPinMode(pin, PINMODE_OUTPUT);
    }

    public void analogWrite(int pin, int duty) {
        // simple approximation: convert duty (0..255) to DC voltage
        double ratio = Math.max(0, Math.min(255, duty)) / 255.0;
        double v = ratio * hw.vcc;
        hw.writePinVoltage(pin, v);
        hw.setPinMode(pin, PINMODE_OUTPUT);
    }

    public int analogRead(int analogIndex) {
        // hardware provides latest sampled analog values (0..1023)
        return hw.getAnalogValue(analogIndex);
    }

    public int digitalRead(int pin) {
        double v = hw.readPinVoltage(pin);
        return v > (hw.vcc * 0.6) ? 1 : 0;
    }

    public void pinMode(int pin, int mode) {
        hw.setPinMode(pin, mode);
    }

    // ---- helpers to load built-in examples (Blink, Fade) ----
    public void loadExample(int exampleIndex) {
        setupInstrs.clear();
        loopInstrs.clear();
        pc = 0;
        setupDone = false;

        switch (exampleIndex) {
            case 0: // Blink (Pin 13)
                setupInstrs.add(new InstrPinMode(13, PINMODE_OUTPUT));
                loopInstrs.add(new InstrDigitalWrite(13, true));
                loopInstrs.add(new InstrDelay(1000));
                loopInstrs.add(new InstrDigitalWrite(13, false));
                loopInstrs.add(new InstrDelay(1000));
                break;

            case 1: // Fade (Pin 9)
                setupInstrs.add(new InstrPinMode(9, PINMODE_OUTPUT));
                // simple fade: write increasing PWM values and loop
                for (int b = 0; b <= 255; b += 5) {
                    loopInstrs.add(new InstrAnalogWrite(9, b));
                    loopInstrs.add(new InstrDelay(30));
                }
                for (int b = 255; b >= 0; b -= 5) {
                    loopInstrs.add(new InstrAnalogWrite(9, b));
                    loopInstrs.add(new InstrDelay(30));
                }
                break;

            case 2: // Button example basic skeleton (assumes external wiring)
                // We'll set pin 13 as OUTPUT and pin 2 as INPUT. The runtime does not yet implement attach interrupts.
                setupInstrs.add(new InstrPinMode(13, PINMODE_OUTPUT));
                setupInstrs.add(new InstrPinMode(2, PINMODE_INPUT));
                // loop: read digital pin 2 and write to 13 (we'll implement simple conditional Instr later)
                // For now, insert a placeholder that reads and writes; use a custom InstrReadWrite
                loopInstrs.add(new InstrReadWrite(2, 13));
                loopInstrs.add(new InstrDelay(50));
                break;

            case 3: // AnalogRead skeleton
                setupInstrs.add(new InstrPinMode(13, PINMODE_OUTPUT));
                loopInstrs.add(new InstrAnalogThreshold(0, 512, 13)); // if A0>512 -> digitalWrite(13,HIGH) else LOW
                loopInstrs.add(new InstrDelay(100));
                break;

            default:
                // default to blink
                loadExample(0);
                break;
        }
    }
}
