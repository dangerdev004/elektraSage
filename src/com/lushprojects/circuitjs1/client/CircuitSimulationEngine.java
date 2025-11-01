/*    
    Copyright (C) Paul Falstad and Iain Sharp
    
    This file is part of CircuitJS1.

    CircuitJS1 is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    CircuitJS1 is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CircuitJS1.  If not, see <http://www.gnu.org/licenses/>.
*/

package com.lushprojects.circuitjs1.client;

import java.util.Vector;

/**
 * CircuitSimulationEngine
 * 
 * This class encapsulates the core circuit simulation logic, separated from UI concerns.
 * It handles:
 * - Modified Nodal Analysis (MNA) matrix operations
 * - Circuit stamping and analysis
 * - Timestep management and convergence
 * - Node voltage calculations
 * - Wire current computations
 */
public class CircuitSimulationEngine {
    
    // Maximum number of voltage sources supported in the circuit
    private static final int MAX_VOLTAGE_SOURCES = 400;
    
    // Reference to the parent CirSim for accessing shared state
    private CirSim sim;
    
    // Matrix and circuit state
    double circuitMatrix[][], circuitRightSide[], lastNodeVoltages[], nodeVoltages[], origRightSide[], origMatrix[][];
    RowInfo circuitRowInfo[];
    int circuitPermute[];
    int circuitMatrixSize, circuitMatrixFullSize;
    boolean circuitNeedsMap;
    boolean circuitNonLinear;
    
    // Simulation timing
    double t;
    double timeStep;
    double maxTimeStep;
    double minTimeStep;
    double timeStepAccum;
    int timeStepCount;
    
    // Convergence state
    boolean converged;
    int subIterations;
    
    // Element arrays for efficient simulation
    CircuitElm elmArr[];
    ScopeElm scopeElmArr[];
    
    // Voltage sources
    int voltageSourceCount;
    CircuitElm voltageSources[];
    
    // Stop state
    String stopMessage;
    CircuitElm stopElm;
    
    // Debug
    boolean dumpMatrix;
    
    // Performance tracking
    long lastIterTime;
    long lastFrameTime;
    int steps;
    
    /**
     * Constructor
     * @param sim The parent CirSim instance
     */
    public CircuitSimulationEngine(CirSim sim) {
        this.sim = sim;
        this.voltageSources = new CircuitElm[MAX_VOLTAGE_SOURCES];
    }
    
    /**
     * Initialize the simulation engine with default parameters
     */
    public void init() {
        t = 0;
        timeStep = 5e-6;
        maxTimeStep = 5e-6;
        minTimeStep = 1e-12;
        timeStepCount = 0;
        timeStepAccum = 0;
    }
    
    /**
     * Stop the simulation with an error message
     */
    public void stop(String s, CircuitElm ce) {
        stopMessage = s;
        circuitMatrix = null;
        stopElm = ce;
    }
    
    /**
     * Check if the simulation can be stopped
     */
    public boolean isStopped() {
        return stopMessage != null;
    }
    
    /**
     * Get the stop message
     */
    public String getStopMessage() {
        return stopMessage;
    }
    
    /**
     * Get the element that caused the stop
     */
    public CircuitElm getStopElm() {
        return stopElm;
    }
    
    /**
     * Clear the stop state
     */
    public void clearStop() {
        stopMessage = null;
        stopElm = null;
    }
    
    // ========================================================================
    // MATRIX STAMPING METHODS
    // ========================================================================
    
    /**
     * Control voltage source vs with voltage from n1 to n2 (must also call stampVoltageSource())
     */
    public void stampVCVS(int n1, int n2, double coef, int vs) {
        int vn = sim.nodeList.size() + vs;
        stampMatrix(vn, n1, coef);
        stampMatrix(vn, n2, -coef);
    }
    
    /**
     * Stamp independent voltage source #vs, from n1 to n2, amount v
     */
    public void stampVoltageSource(int n1, int n2, int vs, double v) {
        int vn = sim.nodeList.size() + vs;
        stampMatrix(vn, n1, -1);
        stampMatrix(vn, n2, 1);
        stampRightSide(vn, v);
        stampMatrix(n1, vn, 1);
        stampMatrix(n2, vn, -1);
    }
    
    /**
     * Use this if the amount of voltage is going to be updated in doStep(), by updateVoltageSource()
     */
    public void stampVoltageSource(int n1, int n2, int vs) {
        int vn = sim.nodeList.size() + vs;
        stampMatrix(vn, n1, -1);
        stampMatrix(vn, n2, 1);
        stampRightSide(vn);
        stampMatrix(n1, vn, 1);
        stampMatrix(n2, vn, -1);
    }
    
    /**
     * Update voltage source in doStep()
     */
    public void updateVoltageSource(int n1, int n2, int vs, double v) {
        int vn = sim.nodeList.size() + vs;
        stampRightSide(vn, v);
    }
    
    /**
     * Stamp a resistor between nodes n1 and n2 with resistance r
     */
    public void stampResistor(int n1, int n2, double r) {
        double r0 = 1 / r;
        if (Double.isNaN(r0) || Double.isInfinite(r0)) {
            throw new IllegalArgumentException("Invalid resistance value: " + r + " (conductance: " + r0 + ")");
        }
        stampMatrix(n1, n1, r0);
        stampMatrix(n2, n2, r0);
        stampMatrix(n1, n2, -r0);
        stampMatrix(n2, n1, -r0);
    }
    
    /**
     * Stamp conductance between nodes n1 and n2
     */
    public void stampConductance(int n1, int n2, double r0) {
        stampMatrix(n1, n1, r0);
        stampMatrix(n2, n2, r0);
        stampMatrix(n1, n2, -r0);
        stampMatrix(n2, n1, -r0);
    }
    
    /**
     * Specify that current from cn1 to cn2 is equal to voltage from vn1 to vn2, divided by g
     */
    public void stampVCCurrentSource(int cn1, int cn2, int vn1, int vn2, double g) {
        stampMatrix(cn1, vn1, g);
        stampMatrix(cn2, vn2, g);
        stampMatrix(cn1, vn2, -g);
        stampMatrix(cn2, vn1, -g);
    }
    
    /**
     * Stamp a current source from n1 to n2
     */
    public void stampCurrentSource(int n1, int n2, double i) {
        stampRightSide(n1, -i);
        stampRightSide(n2, i);
    }
    
    /**
     * Stamp a current source from n1 to n2 depending on current through vs
     */
    public void stampCCCS(int n1, int n2, int vs, double gain) {
        int vn = sim.nodeList.size() + vs;
        stampMatrix(n1, vn, gain);
        stampMatrix(n2, vn, -gain);
    }
    
    /**
     * Stamp value x in row i, column j, meaning that a voltage change
     * of dv in node j will increase the current into node i by x dv.
     * (Unless i or j is a voltage source node.)
     */
    public void stampMatrix(int i, int j, double x) {
        if (Double.isInfinite(x)) {
            // Log for debugging - in production this would use a proper logger
            System.err.println("Warning: Infinite value in matrix at position [" + i + "," + j + "]");
            // Optionally trigger debugger if available
            if (sim != null) {
                CirSim.debugger();
            }
        }
        if (i > 0 && j > 0) {
            if (circuitNeedsMap) {
                i = circuitRowInfo[i - 1].mapRow;
                RowInfo ri = circuitRowInfo[j - 1];
                if (ri.type == RowInfo.ROW_CONST) {
                    circuitRightSide[i] -= x * ri.value;
                    return;
                }
                j = ri.mapCol;
            } else {
                i--;
                j--;
            }
            circuitMatrix[i][j] += x;
        }
    }
    
    /**
     * Stamp value x on the right side of row i, representing an
     * independent current source flowing into node i
     */
    public void stampRightSide(int i, double x) {
        if (i > 0) {
            if (circuitNeedsMap) {
                i = circuitRowInfo[i - 1].mapRow;
            } else
                i--;
            circuitRightSide[i] += x;
        }
    }
    
    /**
     * Indicate that the value on the right side of row i changes in doStep()
     */
    public void stampRightSide(int i) {
        if (i > 0)
            circuitRowInfo[i - 1].rsChanges = true;
    }
    
    /**
     * Indicate that the values on the left side of row i change in doStep()
     */
    public void stampNonLinear(int i) {
        if (i > 0)
            circuitRowInfo[i - 1].lsChanges = true;
    }
    
    // ========================================================================
    // CIRCUIT STAMPING AND ANALYSIS
    // ========================================================================
    
    /**
     * Stamp the circuit matrix with all element contributions
     * This gets called after something changes in the circuit, and also when auto-adjusting timestep
     */
    public void stampCircuit() {
        int i;
        int matrixSize = sim.nodeList.size() - 1 + voltageSourceCount;
        circuitMatrix = new double[matrixSize][matrixSize];
        circuitRightSide = new double[matrixSize];
        nodeVoltages = new double[sim.nodeList.size() - 1];
        if (lastNodeVoltages == null || lastNodeVoltages.length != nodeVoltages.length)
            lastNodeVoltages = new double[sim.nodeList.size() - 1];
        origMatrix = new double[matrixSize][matrixSize];
        origRightSide = new double[matrixSize];
        circuitMatrixSize = circuitMatrixFullSize = matrixSize;
        circuitRowInfo = new RowInfo[matrixSize];
        circuitPermute = new int[matrixSize];
        for (i = 0; i != matrixSize; i++)
            circuitRowInfo[i] = new RowInfo();
        circuitNeedsMap = false;
        
        // stamp linear circuit elements
        for (i = 0; i != sim.elmList.size(); i++) {
            CircuitElm ce = sim.getElm(i);
            ce.setParentList(sim.elmList);
            ce.stamp();
        }
        
        if (!sim.simplifyMatrix(matrixSize))
            return;
        
        // check if we called stop()
        if (circuitMatrix == null)
            return;
        
        // if a matrix is linear, we can do the lu_factor here instead of
        // needing to do it every frame
        if (!circuitNonLinear) {
            if (!sim.lu_factor(circuitMatrix, circuitMatrixSize, circuitPermute)) {
                stop("Singular matrix!", null);
                return;
            }
        }
        
        // copy elmList to an array to avoid a bunch of calls to canCast() when doing simulation
        elmArr = new CircuitElm[sim.elmList.size()];
        int scopeElmCount = 0;
        for (i = 0; i != sim.elmList.size(); i++) {
            elmArr[i] = sim.elmList.get(i);
            if (elmArr[i] instanceof ScopeElm)
                scopeElmCount++;
        }
        
        // copy ScopeElms to an array to avoid a second pass over entire list of elms during simulation
        scopeElmArr = new ScopeElm[scopeElmCount];
        int j = 0;
        for (i = 0; i != sim.elmList.size(); i++) {
            if (elmArr[i] instanceof ScopeElm)
                scopeElmArr[j++] = (ScopeElm) elmArr[i];
        }
    }
    
    // ========================================================================
    // CIRCUIT EXECUTION
    // ========================================================================
    
    /**
     * Run the circuit simulation for one or more iterations
     */
    public void runCircuit(boolean didAnalyze) {
        if (circuitMatrix == null || sim.elmList.size() == 0) {
            circuitMatrix = null;
            return;
        }
        int iter;
        boolean debugprint = dumpMatrix;
        dumpMatrix = false;
        long steprate = (long) (160 * sim.getIterCount());
        long tm = System.currentTimeMillis();
        long lit = lastIterTime;
        if (lit == 0) {
            lastIterTime = tm;
            return;
        }
        
        // Check if we don't need to run simulation (for very slow simulation speeds).
        // If the circuit changed, do at least one iteration to make sure everything is consistent.
        if (1000 >= steprate * (tm - lastIterTime) && !didAnalyze)
            return;
        
        boolean delayWireProcessing = sim.canDelayWireProcessing();
        
        int timeStepCountAtFrameStart = timeStepCount;
        
        // keep track of iterations completed without convergence issues
        int goodIterations = 100;
        
        int frameTimeLimit = (int) (1000 / sim.minFrameRate);
        
        for (iter = 1;; iter++) {
            if (goodIterations >= 3 && timeStep < maxTimeStep) {
                // things are going well, double the time step
                timeStep = Math.min(timeStep * 2, maxTimeStep);
                CirSim.console("timestep up = " + timeStep + " at " + t);
                stampCircuit();
                goodIterations = 0;
            }
            
            int i, j, subiter;
            for (i = 0; i != elmArr.length; i++)
                elmArr[i].startIteration();
            steps++;
            int subiterCount = (sim.adjustTimeStep && timeStep / 2 > minTimeStep) ? 100 : 5000;
            for (subiter = 0; subiter != subiterCount; subiter++) {
                converged = true;
                subIterations = subiter;
                for (i = 0; i != circuitMatrixSize; i++)
                    circuitRightSide[i] = origRightSide[i];
                if (circuitNonLinear) {
                    for (i = 0; i != circuitMatrixSize; i++)
                        for (j = 0; j != circuitMatrixSize; j++)
                            circuitMatrix[i][j] = origMatrix[i][j];
                }
                for (i = 0; i != elmArr.length; i++)
                    elmArr[i].doStep();
                if (stopMessage != null)
                    return;
                boolean printit = debugprint;
                debugprint = false;
                if (circuitMatrixSize < 8) {
                    // we only need this for debugging purposes, so skip it for large matrices
                    for (j = 0; j != circuitMatrixSize; j++) {
                        for (i = 0; i != circuitMatrixSize; i++) {
                            double x = circuitMatrix[i][j];
                            if (Double.isNaN(x) || Double.isInfinite(x)) {
                                stop("nan/infinite matrix!", null);
                                CirSim.console("circuitMatrix " + i + " " + j + " is " + x);
                                return;
                            }
                        }
                    }
                }
                if (printit) {
                    for (j = 0; j != circuitMatrixSize; j++) {
                        String x = "";
                        for (i = 0; i != circuitMatrixSize; i++)
                            x += circuitMatrix[j][i] + ",";
                        x += "\n";
                        CirSim.console(x);
                    }
                    CirSim.console("done");
                }
                if (circuitNonLinear) {
                    // stop if converged (elements check for convergence in doStep())
                    if (converged && subiter > 0)
                        break;
                    if (!sim.lu_factor(circuitMatrix, circuitMatrixSize, circuitPermute)) {
                        stop("Singular matrix!", null);
                        return;
                    }
                }
                sim.lu_solve(circuitMatrix, circuitMatrixSize, circuitPermute, circuitRightSide);
                applySolvedRightSide(circuitRightSide);
                if (!circuitNonLinear)
                    break;
            }
            if (subiter == subiterCount) {
                // convergence failed
                goodIterations = 0;
                if (sim.adjustTimeStep) {
                    timeStep /= 2;
                    CirSim.console("timestep down to " + timeStep + " at " + t);
                }
                if (timeStep < minTimeStep || !sim.adjustTimeStep) {
                    CirSim.console("convergence failed after " + subiter + " iterations");
                    stop("Convergence failed!", null);
                    break;
                }
                // we reduced the timestep. reset circuit state to the way it was at start of iteration
                setNodeVoltages(lastNodeVoltages);
                stampCircuit();
                continue;
            }
            if (subiter > 5 || timeStep < maxTimeStep)
                CirSim.console("converged after " + subiter + " iterations, timeStep = " + timeStep);
            if (subiter < 3)
                goodIterations++;
            else
                goodIterations = 0;
            t += timeStep;
            timeStepAccum += timeStep;
            if (timeStepAccum >= maxTimeStep) {
                timeStepAccum -= maxTimeStep;
                timeStepCount++;
            }
            for (i = 0; i != elmArr.length; i++)
                elmArr[i].stepFinished();
            if (!delayWireProcessing)
                sim.calcWireCurrents();
            for (i = 0; i != sim.scopeCount; i++)
                sim.scopes[i].timeStep();
            for (i = 0; i != scopeElmArr.length; i++)
                scopeElmArr[i].stepScope();
            sim.callTimeStepHook();
            // save last node voltages so we can restart the next iteration if necessary
            for (i = 0; i != lastNodeVoltages.length; i++)
                lastNodeVoltages[i] = nodeVoltages[i];
            
            tm = System.currentTimeMillis();
            lit = tm;
            // Check whether enough time has elapsed to perform an *additional* iteration after
            // those we have already completed. But limit total computation time to 50ms (20fps) by default
            if ((timeStepCount - timeStepCountAtFrameStart) * 1000 >= steprate * (tm - lastIterTime)
                    || (tm - lastFrameTime > frameTimeLimit))
                break;
            if (!sim.simRunning)
                break;
        }
        lastIterTime = lit;
        if (delayWireProcessing)
            sim.calcWireCurrents();
    }
    
    /**
     * Set node voltages given right side found by solving matrix
     */
    void applySolvedRightSide(double rs[]) {
        int j;
        for (j = 0; j != circuitMatrixFullSize; j++) {
            RowInfo ri = circuitRowInfo[j];
            double res = 0;
            if (ri.type == RowInfo.ROW_CONST)
                res = ri.value;
            else
                res = rs[ri.mapCol];
            if (Double.isNaN(res)) {
                converged = false;
                break;
            }
            if (j < sim.nodeList.size() - 1) {
                nodeVoltages[j] = res;
            } else {
                int ji = j - (sim.nodeList.size() - 1);
                voltageSources[ji].setCurrent(ji, res);
            }
        }
        
        setNodeVoltages(nodeVoltages);
    }
    
    /**
     * Set node voltages in each element given an array of node voltages
     */
    void setNodeVoltages(double nv[]) {
        int j, k;
        for (j = 0; j != sim.elmList.size(); j++) {
            CircuitElm ce = sim.getElm(j);
            int nodeCount = ce.getConnectionNodeCount();
            for (k = 0; k != nodeCount; k++)
                ce.setNodeVoltage(k, nv[ce.getConnectionNode(k)]);
        }
    }
    
    /**
     * Get current simulation time
     */
    public double getTime() {
        return t;
    }
    
    /**
     * Get current timestep
     */
    public double getTimeStep() {
        return timeStep;
    }
    
    /**
     * Set maximum timestep
     */
    public void setMaxTimeStep(double ts) {
        this.maxTimeStep = ts;
        this.timeStep = ts;
    }
    
    /**
     * Get the circuit matrix (for debugging/analysis)
     */
    public double[][] getCircuitMatrix() {
        return circuitMatrix;
    }
    
    /**
     * Get the node voltages array
     */
    public double[] getNodeVoltages() {
        return nodeVoltages;
    }
}
