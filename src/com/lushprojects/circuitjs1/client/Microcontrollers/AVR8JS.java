package com.lushprojects.circuitjs1.client.Microcontrollers;

import jsinterop.annotations.JsPackage;
import jsinterop.annotations.JsType;
import jsinterop.annotations.JsMethod;
import jsinterop.annotations.JsProperty;
import jsinterop.annotations.JsFunction;
import jsinterop.annotations.JsOverlay;
import com.google.gwt.typedarrays.shared.Uint8Array;

/**
 * JsInterop wrapper for avr8js library
 * Allows Java code to interact with the AVR emulator
 */
public class AVR8JS {
    
    // Callback interfaces - MUST be at top level for GWT
    @JsFunction
    @FunctionalInterface
    public interface ByteTransmitCallback {
        void onByte(int byteValue);
    }
    
    @JsFunction
    @FunctionalInterface
    public interface PortListener {
        void onChange(int value, int oldValue);
    }
    
    // Main AVRRunner class
    @JsType(isNative = true, namespace = JsPackage.GLOBAL, name = "AVRRunner")
    public static class AVRRunner {
        
        public AVRRunner(Uint8Array program) {
            
        }
        
        @JsProperty(name = "cpu")
        public native CPU getCpu();
        
        @JsProperty(name = "usart")
        public native USART getUsart();
        
        @JsProperty(name = "portB")
        public native PORT getPortB();
        
        @JsProperty(name = "portC")
        public native PORT getPortC();
        
        @JsProperty(name = "portD")
        public native PORT getPortD();
        
        @JsProperty(name = "timer0")
        public native Timer getTimer0();
        
        @JsProperty(name = "timer1")
        public native Timer getTimer1();
        
        @JsProperty(name = "timer2")
        public native Timer getTimer2();
        
        @JsMethod
        public native void execute(double cpuCycles);
        
        @JsMethod
        public native void stop();
        
        // Read data memory (RAM)
        @JsMethod
        public native int readData(int address);
        
        // Write data memory (RAM)
        @JsMethod
        public native void writeData(int address, int value);
    }
    
    // CPU interface
    @JsType(isNative = true, namespace = JsPackage.GLOBAL)
    public static class CPU {
        @JsProperty(name = "pc")
        public native int getPc();  // Program counter
        
        @JsProperty(name = "cycles")
        public native double getCycles();  // CPU cycles (double for large numbers)
        
        @JsProperty(name = "data")
        public native Uint8Array getData();  // RAM access
    }
    
    // USART (Serial) interface
    @JsType(isNative = true, namespace = JsPackage.GLOBAL)
    public static class USART {
        @JsProperty(name = "onByteTransmit")
        public native void setOnByteTransmit(ByteTransmitCallback callback);
        
        @JsMethod
        public native void writeByte(int value);
    }
    
    // PORT interface (for digital pins)
    @JsType(isNative = true, namespace = JsPackage.GLOBAL)
    public static class PORT {
        @JsMethod
        public native void addListener(PortListener listener);
        
        @JsMethod
        public native void removeListener(PortListener listener);
        
        @JsProperty(name = "portValue")
        public native int getValue();  // Current port value (PORTX register)
        
        @JsProperty(name = "pinState")
        public native int getPinState();  // PIN register value
    }
    
    // Timer interface
    @JsType(isNative = true, namespace = JsPackage.GLOBAL)
    public static class Timer {
        @JsProperty(name = "TCNT")
        public native int getTCNT();  // Timer counter value
        
        @JsProperty(name = "OCRA")
        public native int getOCRA();  // Output compare A
        
        @JsProperty(name = "OCRB")
        public native int getOCRB();  // Output compare B
    }
}