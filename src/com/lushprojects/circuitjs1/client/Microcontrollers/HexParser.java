package com.lushprojects.circuitjs1.client.Microcontrollers;

import com.google.gwt.typedarrays.shared.Uint8Array;
import com.google.gwt.typedarrays.client.Uint8ArrayNative;

/**
 * Parser for Intel HEX format files
 * Converts .hex files into binary arrays for AVR emulator
 */
public class HexParser {
    
    /**
     * Parse Intel HEX format and return as Uint8Array
     * @param hexContent The hex file content as string
     * @return Uint8Array containing the program binary
     */
    public static Uint8Array parseHex(String hexContent) {
        // Arduino Uno has 32KB flash
        Uint8Array program = Uint8ArrayNative.create(32768);
        
        // Initialize with 0xFF (unprogrammed flash state)
        for (int i = 0; i < 32768; i++) {
            program.set(i, 0xFF);
        }
        
        String[] lines = hexContent.split("\n");
        
        for (String line : lines) {
            line = line.trim();
            
            if (line.isEmpty() || line.charAt(0) != ':') {
                continue;
            }
            
            try {
                // Parse Intel HEX line
                int byteCount = parseHexByte(line, 1);
                int address = parseHexWord(line, 3);
                int recordType = parseHexByte(line, 7);
                
                if (recordType == 0x00) { // Data record
                    for (int i = 0; i < byteCount; i++) {
                        int dataByte = parseHexByte(line, 9 + i * 2);
                        if (address + i < 32768) {
                            program.set(address + i, dataByte);
                        }
                    }
                } else if (recordType == 0x01) { // End of file
                    break;
                }
                
            } catch (Exception e) {
                consoleLog("Error parsing hex line: " + line);
                consoleLog("Error: " + e.getMessage());
            }
        }
        
        return program;
    }
    
    /**
     * Parse a hex byte (2 characters) from string
     */
    private static int parseHexByte(String hex, int offset) {
        String byteStr = hex.substring(offset, offset + 2);
        return Integer.parseInt(byteStr, 16);
    }
    
    /**
     * Parse a hex word (4 characters, 2 bytes) from string
     */
    private static int parseHexWord(String hex, int offset) {
        String wordStr = hex.substring(offset, offset + 4);
        return Integer.parseInt(wordStr, 16);
    }
    
    /**
     * Native console.log for debugging
     */
    private static native void consoleLog(String message) /*-{
        console.log(message);
    }-*/;
}