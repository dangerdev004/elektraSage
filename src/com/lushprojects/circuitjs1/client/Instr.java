package com.lushprojects.circuitjs1.client;

/**
 * Instruction interface and a few instruction implementations.
 *
 * Each Instr.execute(rt) returns true when the instruction completed successfully and
 * the runtime should advance to the next instruction; returns false when the
 * instruction is still waiting (e.g. Delay).
 *
 * Add more instructions (conditionals, loops, function calls) as needed.
 */
public interface Instr {
    /**
     * Execute instruction. Return true if instruction completed (advance PC).
     * Return false if instruction needs to block and be retried later (e.g. Delay).
     */
    boolean execute(ArduinoRuntime rt);
}

/* ---------- Implementations ---------- */

class InstrPinMode implements Instr {
    final int pin;
    final int mode;
    public InstrPinMode(int pin, int mode) { this.pin = pin; this.mode = mode; }
    public boolean execute(ArduinoRuntime rt) {
        rt.pinMode(pin, mode);
        return true;
    }
}

class InstrDigitalWrite implements Instr {
    final int pin;
    final boolean value;
    public InstrDigitalWrite(int pin, boolean value) { this.pin = pin; this.value = value; }
    public boolean execute(ArduinoRuntime rt) {
        rt.digitalWrite(pin, value);
        return true;
    }
}

class InstrAnalogWrite implements Instr {
    final int pin;
    final int duty;
    public InstrAnalogWrite(int pin, int duty) { this.pin = pin; this.duty = duty; }
    public boolean execute(ArduinoRuntime rt) {
        rt.analogWrite(pin, duty);
        return true;
    }
}

class InstrDelay implements Instr {
    final long millis;
    long targetTime = -1;
    public InstrDelay(long ms) { this.millis = ms; }
    public boolean execute(ArduinoRuntime rt) {
        if (targetTime < 0) {
            targetTime = rt.millis() + millis;
        }
        if (rt.millis() >= targetTime) {
            targetTime = -1;
            return true;
        }
        return false; // still waiting
    }
}

/**
 * Simple instruction that reads a digital pin and writes it to an output pin.
 * Useful for the Button example (pin read -> led).
 */
class InstrReadWrite implements Instr {
    final int readPin;
    final int writePin;
    public InstrReadWrite(int readPin, int writePin) { this.readPin = readPin; this.writePin = writePin; }
    public boolean execute(ArduinoRuntime rt) {
        int val = rt.digitalRead(readPin);
        rt.digitalWrite(writePin, val != 0);
        return true;
    }
}

/**
 * Check analog threshold and set a digital pin accordingly.
 */
class InstrAnalogThreshold implements Instr {
    final int analogIndex;
    final int threshold;
    final int digitalPin;
    public InstrAnalogThreshold(int analogIndex, int threshold, int digitalPin) {
        this.analogIndex = analogIndex;
        this.threshold = threshold;
        this.digitalPin = digitalPin;
    }
    public boolean execute(ArduinoRuntime rt) {
        int v = rt.analogRead(analogIndex);
        rt.digitalWrite(digitalPin, v > threshold);
        return true;
    }
}

class InstrDigitalIfElse implements Instr {

    final int readPin;        // e.g. 2
    final Instr thenInstr;    // e.g. digitalWrite(10, HIGH)
    final Instr elseInstr;    // e.g. digitalWrite(10, LOW)

    public InstrDigitalIfElse(int readPin, Instr thenInstr, Instr elseInstr) {
        this.readPin = readPin;
        this.thenInstr = thenInstr;
        this.elseInstr = elseInstr;
    }

    @Override
    public boolean execute(ArduinoRuntime rt) {
        int value = rt.digitalRead(readPin);
        if (value != 0) {
            thenInstr.execute(rt);
        } else {
            elseInstr.execute(rt);
        }
        return true;
    }
}
