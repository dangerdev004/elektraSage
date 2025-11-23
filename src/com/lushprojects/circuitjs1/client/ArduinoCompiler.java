package com.lushprojects.circuitjs1.client;

import java.util.ArrayList;
import java.util.List;

/**
 * ArduinoCompiler
 *
 * Translates your AST (from ArduinoParser) into the IR instructions (Instr).
 *
 * Supports a small, useful subset:
 *  - pinMode(pin, MODE)
 *  - digitalWrite(pin, HIGH/LOW)
 *  - analogWrite(pin, value)
 *  - delay(ms)
 *  - int x = analogRead(A#);
 *  - if (x > CONST) { digitalWrite(pin,HIGH); } else { digitalWrite(pin,LOW); }
 *
 * For recognized analog-read + threshold patterns we emit InstrAnalogThreshold for efficiency.
 *
 * Usage:
 *   AST.Program prog = ArduinoParser.parseProgram(src);
 *   ArduinoCompiler.CompileResult res = ArduinoCompiler.compile(prog);
 *   runtime.setupInstrs = res.setup;
 *   runtime.loopInstrs  = res.loop;
 */
public class ArduinoCompiler {

    public static class CompileResult {
        public final List<Instr> setup = new ArrayList<>();
        public final List<Instr> loop  = new ArrayList<>();
    }

    /**
     * Compile an AST.Program into IR lists for setup() and loop().
     */
    public static CompileResult compile(AST.Program prog) {
        CompileResult out = new CompileResult();

        // find setup() and loop()
        for (AST.FunctionDecl f : prog.functions) {
            if ("setup".equals(f.name)) {
                out.setup.addAll(compileStmtList(f.body));
            } else if ("loop".equals(f.name)) {
                out.loop.addAll(compileStmtList(f.body));
            } else {
                // ignore other functions for the minimal compiler
                System.err.println("Compiler: ignoring function " + f.name);
            }
        }

        return out;
    }

    // Compile a list of AST statements into Instrs
    private static List<Instr> compileStmtList(List<AST.Stmt> stmts) {
        List<Instr> list = new ArrayList<>();
        for (int i = 0; i < stmts.size(); i++) {
            AST.Stmt s = stmts.get(i);

            // Pattern: var decl assigned from analogRead followed by if (var > CONST) { dw(HIGH) } else { dw(LOW) }
            if (s instanceof AST.StmtVarDecl) {
                AST.StmtVarDecl vd = (AST.StmtVarDecl) s;
                if (vd.init instanceof AST.ExprCall) {
                    AST.ExprCall call = (AST.ExprCall) vd.init;
                    if ("analogRead".equals(call.name) && call.args.size() == 1) {
                        Integer analogIndex = extractAnalogIndexFromExpr(call.args.get(0));
                        if (analogIndex != null && i + 1 < stmts.size() && stmts.get(i+1) instanceof AST.StmtIf) {
                            AST.StmtIf nextIf = (AST.StmtIf) stmts.get(i+1);
                            // condition should be var > literal
                            if (nextIf.cond instanceof AST.ExprBinary) {
                                AST.ExprBinary bin = (AST.ExprBinary) nextIf.cond;
                                if (">".equals(bin.op) && bin.left instanceof AST.ExprVar && bin.right instanceof AST.ExprLiteral) {
                                    AST.ExprVar leftVar = (AST.ExprVar) bin.left;
                                    if (leftVar.name.equals(vd.name)) {
                                        int threshold = ((AST.ExprLiteral) bin.right).value;
                                        // check then/else bodies for single digitalWrite to a pin
                                        Integer truePin = extractSingleDigitalWritePin(nextIf.thenStmt);
                                        Integer falsePin = extractSingleDigitalWritePin(nextIf.elseStmt);
                                        if (truePin != null && falsePin != null && truePin.equals(falsePin)) {
                                            // common pattern: if (x > T) digitalWrite(p, HIGH); else digitalWrite(p, LOW);
                                            int digitalPin = truePin;
                                            list.add(new InstrAnalogThreshold(analogIndex, threshold, digitalPin));
                                            // skip next if statement because we've compiled it
                                            i++; // skip the if
                                            continue;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Normal translations
            if (s instanceof AST.StmtExpr) {
                AST.StmtExpr se = (AST.StmtExpr) s;
                compileExprStatement(se.expr, list);
            } else if (s instanceof AST.StmtIf) {
                // try to compile if(stmt) where condition is simple analogRead compare
                AST.StmtIf sif = (AST.StmtIf) s;
                boolean compiled = tryCompileIfSimple(sif, list);
                if (!compiled) {
                    System.err.println("Compiler: skipping complex if at top-level (not supported by minimal compiler).");
                }
            } else if (s instanceof AST.StmtVarDecl) {
                AST.StmtVarDecl sv = (AST.StmtVarDecl) s;
                // var declaration with init that is an expression we can emit (e.g. calling analogRead alone)
                if (sv.init instanceof AST.ExprCall) {
                    AST.ExprCall call = (AST.ExprCall) sv.init;
                    if ("analogRead".equals(call.name) && call.args.size() == 1) {
                        Integer analogIndex = extractAnalogIndexFromExpr(call.args.get(0));
                        if (analogIndex != null) {
                            // We don't have variable storage in runtime; warn and emit the analogRead as a no-op
                            System.err.println("Compiler: local var '" + sv.name + "' assigned analogRead - variable storage not supported; try using direct if(analogRead(...)).");
                        }
                    }
                }
            } else if (s instanceof AST.StmtWhile) {
                // minimal support: not implemented
                System.err.println("Compiler: while loops not supported in minimal compiler.");
            } else if (s instanceof AST.StmtReturn) {
                // ignore returns in setup/loop
            } else if (s instanceof AST.StmtAssign) {
                // assignment not widely supported - try to handle direct analogRead assignment pattern
                AST.StmtAssign sa = (AST.StmtAssign) s;
                if (sa.value instanceof AST.ExprCall) {
                    AST.ExprCall call = (AST.ExprCall) sa.value;
                    if ("analogRead".equals(call.name) && call.args.size() == 1) {
                        System.err.println("Compiler: assignment of analogRead to variable not supported in minimal flow.");
                    }
                }
            } else if (s instanceof AST.StmtBlock) {
                AST.StmtBlock b = (AST.StmtBlock) s;
                list.addAll(compileStmtList(b.stmts));
            } else {
                System.err.println("Compiler: unrecognized statement type: " + s.getClass().getSimpleName());
            }
        }
        return list;
    }

    // handle expression statements such as pinMode(...); digitalWrite(...); analogWrite(...); delay(...);
    private static void compileExprStatement(AST.Expr e, List<Instr> out) {
        if (e instanceof AST.ExprCall) {
            AST.ExprCall c = (AST.ExprCall) e;
            String name = c.name;
            if ("pinMode".equals(name) && c.args.size() == 2) {
                Integer pin = extractIntFromExpr(c.args.get(0));
                int mode = ArduinoRuntime.PINMODE_INPUT;
                String arg2 = exprToString(c.args.get(1));
                if (arg2 != null && arg2.contains("OUTPUT")) mode = ArduinoRuntime.PINMODE_OUTPUT;
                if (arg2 != null && arg2.contains("INPUT_PULLUP")) mode = ArduinoRuntime.PINMODE_INPUT_PULLUP;
                if (pin != null) out.add(new InstrPinMode(pin, mode));
                return;
            }
            if ("digitalWrite".equals(name) && c.args.size() == 2) {
                Integer pin = extractIntFromExpr(c.args.get(0));
                Boolean val = extractHighLowFromExpr(c.args.get(1));
                if (pin != null && val != null) out.add(new InstrDigitalWrite(pin, val));
                return;
            }
            if ("analogWrite".equals(name) && c.args.size() == 2) {
                Integer pin = extractIntFromExpr(c.args.get(0));
                Integer duty = extractIntFromExpr(c.args.get(1));
                if (pin != null && duty != null) out.add(new InstrAnalogWrite(pin, duty));
                return;
            }
            if ("delay".equals(name) && c.args.size() == 1) {
                Integer ms = extractIntFromExpr(c.args.get(0));
                if (ms != null) out.add(new InstrDelay(ms));
                return;
            }
            if ("analogRead".equals(name)) {
                // standalone analogRead(...) used as expression - not stored; ignore
                return;
            }

            System.err.println("Compiler: unknown function call '" + name + "' or unsupported args.");
            return;
        }
        // other expressions ignored for now
        System.err.println("Compiler: unsupported expression statement: " + e.getClass().getSimpleName());
    }

    // Try to compile a simple if-of-analog-read pattern directly into InstrAnalogThreshold,
    // or compile trivial digitalWrite branches into sequences.
    private static boolean tryCompileIfSimple(AST.StmtIf sif, List<Instr> out) {
        AST.Expr cond = sif.cond;
        // Pattern B: if (digitalRead(pin)) { digitalWrite(..., HIGH) } else { digitalWrite(..., LOW) }

        if (cond instanceof AST.ExprCall) {
            AST.ExprCall call = (AST.ExprCall) cond;
            if ("digitalRead".equals(call.name) && call.args.size() == 1) {
                Integer readPin = extractIntFromExpr(call.args.get(0));
                if (readPin != null) {
                    // extract digitalWrite from then/else
                    Integer thenPin = extractSingleDigitalWritePin(sif.thenStmt);
                    Boolean thenVal = extractSingleDigitalWriteValue(sif.thenStmt);
                    Integer elsePin = extractSingleDigitalWritePin(sif.elseStmt);
                    Boolean elseVal = extractSingleDigitalWriteValue(sif.elseStmt);

                    if (thenPin != null && thenVal != null &&
                        elsePin != null && elseVal != null &&
                        thenPin.equals(elsePin)) {

                        Instr thenInstr = new InstrDigitalWrite(thenPin, thenVal);
                        Instr elseInstr = new InstrDigitalWrite(elsePin, elseVal);
                        out.add(new InstrDigitalIfElse(readPin, thenInstr, elseInstr));
                        return true;
                    }
                }
            }
        }
        
        // Pattern A: analogRead(Ax) > CONST
        if (cond instanceof AST.ExprBinary) {
            AST.ExprBinary bin = (AST.ExprBinary) cond;
            if (">".equals(bin.op)) {
                Integer analogIndex = null;
                Integer threshold = null;
                // left can be analogRead(...) or a literal var representing analogRead (not supported here)
                if (bin.left instanceof AST.ExprCall) {
                    AST.ExprCall leftCall = (AST.ExprCall) bin.left;
                    if ("analogRead".equals(leftCall.name) && leftCall.args.size() == 1) {
                        analogIndex = extractAnalogIndexFromExpr(leftCall.args.get(0));
                    }
                }
                if (bin.right instanceof AST.ExprLiteral) {
                    threshold = ((AST.ExprLiteral) bin.right).value;
                }
                if (analogIndex != null && threshold != null) {
                    // try to detect simple branches that are single digitalWrite to same pin with HIGH/LOW
                    Integer truePin = extractSingleDigitalWritePin(sif.thenStmt);
                    Integer falsePin = extractSingleDigitalWritePin(sif.elseStmt);
                    if (truePin != null && falsePin != null && truePin.equals(falsePin)) {
                        out.add(new InstrAnalogThreshold(analogIndex, threshold, truePin));
                        return true;
                    } else {
                        // fallback: compile then/else blocks recursively (but we don't have runtime conditional instr)
                        // so we cannot represent arbitrary if; report unsupported
                        System.err.println("Compiler: complex if branches with analog condition not compiled to threshold optimization.");
                    }
                }
            }
        }
        // other condition patterns not supported here
        return false;
    }

    // Extract simple digitalWrite pin from a statement if it is a single digitalWrite(...);
    // returns pin number or null
    private static Integer extractSingleDigitalWritePin(AST.Stmt stmt) {
        if (stmt == null) return null;
        // unwrap block with single statement
        if (stmt instanceof AST.StmtBlock) {
            AST.StmtBlock b = (AST.StmtBlock) stmt;
            if (b.stmts.size() == 1) return extractSingleDigitalWritePin(b.stmts.get(0));
            return null;
        }
        if (stmt instanceof AST.StmtExpr) {
            AST.StmtExpr se = (AST.StmtExpr) stmt;
            if (se.expr instanceof AST.ExprCall) {
                AST.ExprCall call = (AST.ExprCall) se.expr;
                if ("digitalWrite".equals(call.name) && call.args.size() == 2) {
                    Integer pin = extractIntFromExpr(call.args.get(0));
                    // confirm second arg is HIGH or LOW
                    Boolean val = extractHighLowFromExpr(call.args.get(1));
                    if (pin != null && val != null) return pin;
                }
            }
        }
        return null;
    }

    // Utility: extract analog index from expression (A0 -> 0, A1 -> 1, ...).
    private static Integer extractAnalogIndexFromExpr(AST.Expr e) {
        if (e instanceof AST.ExprVar) {
            String n = ((AST.ExprVar) e).name;
            if (n.length() >= 2 && (n.charAt(0) == 'A' || n.charAt(0) == 'a')) {
                try {
                    int idx = Integer.parseInt(n.substring(1));
                    if (idx >= 0 && idx <= 5) return idx;
                } catch (NumberFormatException ignored) {}
            }
        }
        // also allow literal numeric pin -> not analog index in that case
        return null;
    }

    // Extract integer literal from expression (very simple)
    private static Integer extractIntFromExpr(AST.Expr e) {
        if (e instanceof AST.ExprLiteral) {
            return ((AST.ExprLiteral) e).value;
        }
        if (e instanceof AST.ExprVar) {
            // sometimes user uses numeric literal as var (not supported), return null
            try {
                String s = ((AST.ExprVar) e).name;
                return Integer.parseInt(s);
            } catch (Exception ex) { /* ignore */ }
        }
        // expressions like (13) will have been parsed into ExprLiteral already by parser
        return null;
    }

    // Extract HIGH/LOW from expression (IDENT HIGH/LOW)
    private static Boolean extractHighLowFromExpr(AST.Expr e) {
        if (e instanceof AST.ExprVar) {
            String s = ((AST.ExprVar) e).name;
            if ("HIGH".equals(s)) return Boolean.TRUE;
            if ("LOW".equals(s)) return Boolean.FALSE;
        }
        return null;
    }

    // Represent an expression as a string (used for pinMode mode detection)
    private static String exprToString(AST.Expr e) {
        if (e == null) return null;
        if (e instanceof AST.ExprVar) return ((AST.ExprVar) e).name;
        if (e instanceof AST.ExprLiteral) return Integer.toString(((AST.ExprLiteral) e).value);
        return e.toString();
    }

    private static Boolean extractSingleDigitalWriteValue(AST.Stmt stmt) {
        if (stmt == null) return null;
        if (stmt instanceof AST.StmtBlock) {
            AST.StmtBlock b = (AST.StmtBlock) stmt;
            if (b.stmts.size() == 1) return extractSingleDigitalWriteValue(b.stmts.get(0));
        }
        if (stmt instanceof AST.StmtExpr) {
            AST.StmtExpr se = (AST.StmtExpr) stmt;
            if (se.expr instanceof AST.ExprCall) {
                AST.ExprCall call = (AST.ExprCall) se.expr;
                if ("digitalWrite".equals(call.name) && call.args.size() == 2) {
                    return extractHighLowFromExpr(call.args.get(1));
                }
            }
        }
        return null;
    }
}