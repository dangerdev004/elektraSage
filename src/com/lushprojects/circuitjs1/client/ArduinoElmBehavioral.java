package com.lushprojects.circuitjs1.client;

/**
 * JavaScript bridge for behavioral Arduino simulation.
 * Provides JSNI methods to interact with JavaScript-based MCU simulation.
 */
public class ArduinoElmBehavioral {
    private static ArduinoElm currentArduino;

    /**
     * Set the current Arduino instance for callbacks
     */
    public static void setCurrentBehavioralArduino(ArduinoElm arduino) {
        currentArduino = arduino;
    }

    /**
     * Get the current Arduino instance
     */
    public static ArduinoElm getCurrentBehavioralArduino() {
        return currentArduino;
    }

    /**
     * Bind the circuit adapter to window.CircuitAdapter
     * This allows JavaScript code to interact with the circuit simulation
     */
    public static native void jsBindCircuitAdapter() /*-{
        if (!$wnd.CircuitAdapter) {
            $wnd.CircuitAdapter = {
                // Called by JS to set a pin's target voltage
                setPinVoltage: function(arduinoId, pinIdx, voltage) {
                    var arduino = @com.lushprojects.circuitjs1.client.ArduinoElmBehavioral::getCurrentBehavioralArduino()();
                    if (arduino) {
                        arduino.@com.lushprojects.circuitjs1.client.ArduinoElm::setBehavioralPinVoltage(ID)(pinIdx, voltage);
                    }
                },
                
                // Called by JS to read a pin's current voltage
                getPinVoltage: function(arduinoId, pinIdx) {
                    var arduino = @com.lushprojects.circuitjs1.client.ArduinoElmBehavioral::getCurrentBehavioralArduino()();
                    if (arduino) {
                        return arduino.@com.lushprojects.circuitjs1.client.ArduinoElm::getPinVoltage(I)(pinIdx);
                    }
                    return 0.0;
                },
                
                // Get current simulation time
                getTime: function() {
                    return @com.lushprojects.circuitjs1.client.CirSim::theSim.@com.lushprojects.circuitjs1.client.CirSim::t;
                },
                
                // Log to console
                log: function(msg) {
                    @com.lushprojects.circuitjs1.client.CirSim::console(Ljava/lang/String;)(msg);
                }
            };
        }
    }-*/;

    /**
     * Create a behavioral MCU instance in JavaScript
     * @param pinMap Array of circuit node indices for each pin
     * @param setupCode JavaScript setup code (runs once)
     * @param loopCode JavaScript loop code (runs repeatedly)
     * @param pinCount Number of pins
     * @param id Unique identifier for this MCU instance
     * @return Instance ID string
     */
    public static native String jsCreateBehavioralMCU(int[] pinMap, String setupCode, 
                                                      String loopCode, int pinCount, String id) /*-{
        if (!$wnd.BehavioralMCU) {
            $wnd.BehavioralMCU = {};
        }
        
        var mcu = {
            id: id,
            pinMap: pinMap,
            setupCode: setupCode,
            loopCode: loopCode,
            pinCount: pinCount,
            state: {},
            setupRun: false,
            lastLoopTime: 0,
            loopInterval: 0.02, // Run loop ~50Hz
            
            // Helper functions available to user code
            digitalWrite: function(pin, value) {
                var voltage = value ? 5.0 : 0.0;
                if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.setPinVoltage) {
                    $wnd.CircuitAdapter.setPinVoltage(id, pin, voltage);
                }
            },
            
            digitalRead: function(pin) {
                if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.getPinVoltage) {
                    var v = $wnd.CircuitAdapter.getPinVoltage(id, pin);
                    return v > 2.5 ? 1 : 0;
                }
                return 0;
            },
            
            analogWrite: function(pin, value) {
                var voltage = (value / 255.0) * 5.0;
                if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.setPinVoltage) {
                    $wnd.CircuitAdapter.setPinVoltage(id, pin, voltage);
                }
            },
            
            analogRead: function(pin) {
                if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.getPinVoltage) {
                    var v = $wnd.CircuitAdapter.getPinVoltage(id, pin);
                    return Math.round((v / 5.0) * 1023);
                }
                return 0;
            },
            
            time: function() {
                if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.getTime) {
                    return $wnd.CircuitAdapter.getTime();
                }
                return 0;
            },
            
            log: function(msg) {
                if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.log) {
                    $wnd.CircuitAdapter.log(msg);
                }
            }
        };
        
        $wnd.BehavioralMCU[id] = mcu;
        return id;
    }-*/;

    /**
     * Start the behavioral MCU simulation
     */
    public static native void jsStartBehavioralMCU(String id) /*-{
        if (!$wnd.BehavioralMCU || !$wnd.BehavioralMCU[id]) {
            console.error("BehavioralMCU instance not found: " + id);
            return;
        }
        
        var mcu = $wnd.BehavioralMCU[id];
        
        // Initialize state if needed
        if (!mcu.state._initialized) {
            mcu.state._initialized = true;
            mcu.state._pinModes = {};
            mcu.state._delayStart = 0;
            mcu.state._delaying = false;
            mcu.state._delayDuration = 0;
        }
        
        // Run setup code once
        if (!mcu.setupRun && mcu.setupCode) {
            try {
                console.log("Running setup code:", mcu.setupCode);
                console.log("MCU object keys:", Object.keys(mcu));
                console.log("MCU has digitalWrite?", typeof mcu.digitalWrite);
                console.log("Testing direct call:", typeof mcu.digitalWrite);
                var setupFn = new Function('ctx', 'console.log("In setup, ctx:", ctx, "ctx.digitalWrite:", ctx.digitalWrite); ' + mcu.setupCode);
                setupFn(mcu);
                mcu.setupRun = true;
                console.log("Setup complete");
            } catch (e) {
                console.error("Error in setup code:", e);
                if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.log) {
                    $wnd.CircuitAdapter.log("Setup error: " + e.message);
                }
            }
        }
        
        // Schedule loop execution
        if (!mcu.loopTimer) {
            console.log("Starting loop timer with interval:", mcu.loopInterval * 1000, "ms");
            console.log("Loop code:", mcu.loopCode);
            console.log("MCU methods available:", Object.keys(mcu));
            mcu.loopTimer = setInterval(function() {
                if (mcu.loopCode) {
                    try {
                        var loopFn = new Function('ctx', 'console.log("In loop, ctx type:", typeof ctx, "has digitalWrite:", typeof ctx.digitalWrite); ' + mcu.loopCode);
                        loopFn(mcu);
                    } catch (e) {
                        console.error("Error in loop code:", e);
                        console.error("Generated code was:", mcu.loopCode);
                        if ($wnd.CircuitAdapter && $wnd.CircuitAdapter.log) {
                            $wnd.CircuitAdapter.log("Loop error: " + e.message);
                        }
                    }
                }
            }, mcu.loopInterval * 1000);
        }
    }-*/;

    /**
     * Destroy a behavioral MCU instance
     */
    public static native void jsDestroyBehavioralMCU(String id) /*-{
        if ($wnd.BehavioralMCU && $wnd.BehavioralMCU[id]) {
            var mcu = $wnd.BehavioralMCU[id];
            if (mcu.loopTimer) {
                clearInterval(mcu.loopTimer);
                mcu.loopTimer = null;
            }
            delete $wnd.BehavioralMCU[id];
        }
    }-*/;

    /**
     * Transpile Arduino C++ code to JavaScript setup/loop functions
     * @param arduinoCode Arduino sketch in C++
     * @return Array [setupJS, loopJS]
     */
    public static String[] transpileArduinoToJS(String arduinoCode) {
        String setupJS = "";
        String loopJS = "";
        
        // Extract setup() function
        int setupStart = arduinoCode.indexOf("void setup()");
        if (setupStart >= 0) {
            int setupBodyStart = arduinoCode.indexOf("{", setupStart);
            int setupBodyEnd = findMatchingBrace(arduinoCode, setupBodyStart);
            if (setupBodyStart >= 0 && setupBodyEnd > setupBodyStart) {
                String setupBody = arduinoCode.substring(setupBodyStart + 1, setupBodyEnd).trim();
                setupJS = transpileArduinoBlock(setupBody, true);
            }
        }
        
        // Extract loop() function
        int loopStart = arduinoCode.indexOf("void loop()");
        if (loopStart >= 0) {
            int loopBodyStart = arduinoCode.indexOf("{", loopStart);
            int loopBodyEnd = findMatchingBrace(arduinoCode, loopBodyStart);
            if (loopBodyStart >= 0 && loopBodyEnd > loopBodyStart) {
                String loopBody = arduinoCode.substring(loopBodyStart + 1, loopBodyEnd).trim();
                loopJS = transpileArduinoBlock(loopBody, false);
            }
        }
        
        // Extract global variables (before setup/loop)
        String globals = "";
        int firstFunctionStart = Math.min(
            setupStart >= 0 ? setupStart : Integer.MAX_VALUE,
            loopStart >= 0 ? loopStart : Integer.MAX_VALUE
        );
        if (firstFunctionStart < Integer.MAX_VALUE && firstFunctionStart > 0) {
            globals = arduinoCode.substring(0, firstFunctionStart).trim();
            globals = transpileGlobalVariables(globals);
        }
        
        // Prepend globals to setup
        if (!globals.isEmpty()) {
            setupJS = globals + "\n" + setupJS;
        }
        
        return new String[] { setupJS, loopJS };
    }
    
    private static int findMatchingBrace(String code, int openBracePos) {
        if (openBracePos < 0 || openBracePos >= code.length()) return -1;
        int depth = 0;
        for (int i = openBracePos; i < code.length(); i++) {
            char c = code.charAt(i);
            if (c == '{') depth++;
            else if (c == '}') {
                depth--;
                if (depth == 0) return i;
            }
        }
        return -1;
    }
    
    private static String transpileGlobalVariables(String globals) {
        // Remove comments
        globals = globals.replaceAll("//[^\\n]*", "");
        globals = globals.replaceAll("/\\*.*?\\*/", "");
        
        StringBuilder js = new StringBuilder();
        String[] lines = globals.split(";");
        
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) continue;
            
            // Convert variable declarations: int x = 5; -> ctx.state.x = 5;
            if (line.matches("^(int|float|double|long|byte|bool|boolean)\\s+\\w+.*")) {
                String[] parts = line.split("\\s+", 2);
                if (parts.length == 2) {
                    String varDecl = parts[1].trim();
                    // Handle: varName = value or just varName
                    if (varDecl.contains("=")) {
                        String[] varParts = varDecl.split("=", 2);
                        String varName = varParts[0].trim();
                        String varValue = varParts[1].trim();
                        js.append("ctx.state.").append(varName).append(" = ").append(varValue).append(";\n");
                    } else {
                        js.append("ctx.state.").append(varDecl).append(" = 0;\n");
                    }
                }
            }
        }
        
        return js.toString();
    }
    
    private static String transpileArduinoBlock(String code, boolean isSetup) {
        // Remove comments
        code = code.replaceAll("//[^\\n]*", "");
        code = code.replaceAll("/\\*.*?\\*/", "");
        
        StringBuilder js = new StringBuilder();
        if (isSetup) {
            js.append("// Setup\n");
        } else {
            js.append("// Loop with state machine for delays\n");
            js.append("if (!ctx.state._loopStep) ctx.state._loopStep = 0;\n");
            js.append("if (ctx.state._delaying) {\n");
            js.append("  if ((ctx.time() - ctx.state._delayStart) < ctx.state._delayDuration) return;\n");
            js.append("  ctx.state._delaying = false;\n");
            js.append("  ctx.state._loopStep++;\n");
            js.append("}\n");
        }
        
        // Convert delay() calls to state machine steps
        String[] lines = code.split(";");
        int delayCount = 0;
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) continue;
            
            if (line.contains("delay(")) {
                if (!isSetup) {
                    // Add step guard before the delay
                    js.append("if (ctx.state._loopStep === ").append(delayCount).append(") {\n");
                }
                
                // Extract delay value
                String delayMs = line.replaceAll(".*delay\\s*\\(\\s*(\\d+)\\s*\\).*", "$1");
                js.append("  ctx.state._delaying = true;\n");
                js.append("  ctx.state._delayStart = ctx.time();\n");
                js.append("  ctx.state._delayDuration = ").append(delayMs).append(" / 1000.0;\n");
                js.append("  return;\n");
                
                if (!isSetup) {
                    js.append("}\n");
                    delayCount++;
                }
            } else {
                // Regular Arduino code
                if (!isSetup && delayCount > 0) {
                    js.append("if (ctx.state._loopStep === ").append(delayCount).append(") {\n  ");
                }
                
                // First replace constants to avoid issues with replacements
                String jsLine = line
                    .replaceAll("\\bHIGH\\b", "1")
                    .replaceAll("\\bLOW\\b", "0")
                    .replaceAll("\\bOUTPUT\\b", "'OUTPUT'")
                    .replaceAll("\\bINPUT_PULLUP\\b", "'INPUT_PULLUP'")
                    .replaceAll("\\bINPUT\\b", "'INPUT'");
                
                // Replace variable references BEFORE function calls to avoid double ctx
                // But first check if the line even contains these variables to avoid unnecessary replacement
                if (line.matches(".*(brightness|fadeAmount|buttonPin|ledPin|buttonState|sensorPin|sensorValue).*")) {
                    jsLine = jsLine
                        .replaceAll("\\b(brightness|fadeAmount|buttonPin|ledPin|buttonState|sensorPin|sensorValue)\\b", "ctx.state.$1");
                }
                
                // Now replace Arduino functions - use markers to prevent double replacement
                jsLine = jsLine
                    // pinMode(pin, mode)
                    .replaceAll("pinMode\\s*\\(", "CTXMARK_pinMode(")
                    // digitalWrite
                    .replaceAll("digitalWrite\\s*\\(", "CTXMARK_digitalWrite(")
                    // digitalRead(pin)
                    .replaceAll("digitalRead\\s*\\(", "CTXMARK_digitalRead(")
                    // analogWrite(pin, value)
                    .replaceAll("analogWrite\\s*\\(", "CTXMARK_analogWrite(")
                    // analogRead(pin) - handle A0-A5
                    .replaceAll("analogRead\\s*\\(\\s*A(\\d+)\\s*\\)", "CTXMARK_analogRead(14 + $1)")
                    .replaceAll("analogRead\\s*\\(", "CTXMARK_analogRead(");
                
                // Debug: log before marker replacement
                String beforeMarker = jsLine;
                
                // Now replace the markers with actual ctx calls
                jsLine = jsLine
                    .replaceAll("CTXMARK_pinMode\\(\\s*(\\w+[^,]*)\\s*,\\s*([^)]*)\\)", "ctx.state._pinModes[$1] = $2")
                    .replaceAll("CTXMARK_digitalWrite\\(\\s*([^,]+)\\s*,\\s*([^)]+)\\)", "ctx.digitalWrite($1, $2)")
                    .replaceAll("CTXMARK_digitalRead\\(\\s*([^)]+)\\)", "ctx.digitalRead($1)")
                    .replaceAll("CTXMARK_analogWrite\\(\\s*([^,]+)\\s*,\\s*([^)]+)\\)", "ctx.analogWrite($1, $2)")
                    .replaceAll("CTXMARK_analogRead\\(\\s*([^)]+)\\)", "ctx.analogRead($1)");
                
                // Debug: check for double ctx
                if (jsLine.contains("ctx.ctx")) {
                    System.out.println("DEBUG: Double ctx found!");
                    System.out.println("  Original line: " + line);
                    System.out.println("  Before markers: " + beforeMarker);
                    System.out.println("  After markers: " + jsLine);
                }
                
                js.append(jsLine).append(";\n");
                
                if (!isSetup && delayCount > 0) {
                    js.append("}\n");
                }
            }
        }
        
        // Reset loop step at the end
        if (!isSetup) {
            js.append("ctx.state._loopStep = 0;\n");
        }
        
        return js.toString();
    }
}
