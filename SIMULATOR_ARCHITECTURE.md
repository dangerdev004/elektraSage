# CircuitJS1 Simulator - Complete Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Core Simulation Theory](#core-simulation-theory)
3. [System Architecture](#system-architecture)
4. [Main Program Loop](#main-program-loop)
5. [Circuit Element System](#circuit-element-system)
6. [Modified Nodal Analysis (MNA)](#modified-nodal-analysis-mna)
7. [Rendering System](#rendering-system)
8. [Migration to ReactJS](#migration-to-reactjs)
9. [Key Algorithms with Pseudocode](#key-algorithms-with-pseudocode)

---

## Overview

CircuitJS1 is a browser-based electronic circuit simulator originally created in Java as an applet by Paul Falstad and converted to JavaScript using Google Web Toolkit (GWT) by Iain Sharp. 

**Note**: The architecture has been recently refactored to separate UI and simulation concerns. See [ARCHITECTURE_SEGREGATION.md](ARCHITECTURE_SEGREGATION.md) for detailed information about this segregation.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  (CirSim.java - UI/UX Components)                           │
│  - GWT Widgets, Canvas, Menus                               │
│  - Mouse/Keyboard Handlers                                   │
│  - Element editing and placement                             │
└──────────────────┬──────────────────────────────────────────┘
                   │ delegates to
                   │
┌──────────────────▼──────────────────────────────────────────┐
│            Simulation Engine Layer                           │
│  (CircuitSimulationEngine.java - NEW!)                      │
│  - Modified Nodal Analysis (MNA) matrix solver              │
│  - Matrix stamping operations                                │
│  - Timestep management                                       │
│  - Convergence iteration                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │ interacts with
                   │
┌──────────────────▼──────────────────────────────────────────┐
│           Circuit Element Layer                              │
│  (CircuitElm.java and 200+ subclasses)                     │
│  - Resistors, Capacitors, Inductors                         │
│  - Active components (Transistors, Op-Amps)                 │
│  - Digital logic gates                                       │
│  - Complex integrated circuits                               │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Language**: Java (compiled to JavaScript via GWT)
- **UI Framework**: Google Web Toolkit (GWT)
- **Graphics**: HTML5 Canvas
- **Matrix Math**: Custom LU decomposition implementation
- **Storage**: Browser LocalStorage for settings

---

## Core Simulation Theory

The simulation is based on **Modified Nodal Analysis (MNA)**, a standard method for circuit analysis described in the book _"Electronic Circuit and System Simulation Methods"_ by Pillage, Rohrer, and Visweswariah (1999).

### The Fundamental Equation

The core of the simulation solves this matrix equation at each timestep:

```
X = A⁻¹B
```

Where:
- **A** is a square matrix (admittance matrix)
  - One row per circuit node (connection point)
  - One row per independent voltage source
  - Contains conductances (1/resistance) and other element properties
  
- **B** is a column vector (excitation vector)
  - One entry per circuit node
  - One entry per independent voltage source
  - Contains current source values and voltage source values
  
- **X** is the solution vector
  - Contains voltage at each node
  - Contains current through each voltage source
  
- **A⁻¹** is computed via LU decomposition for efficiency

### Why This Works

1. **Kirchhoff's Current Law (KCL)**: Sum of currents at each node = 0
2. **Kirchhoff's Voltage Law (KVL)**: Sum of voltages around any loop = 0
3. **Ohm's Law**: V = IR (or I = V/R = V*G where G is conductance)

The MNA method expresses these laws as a system of linear equations that can be solved using linear algebra.

---

## System Architecture

### Key Classes

#### 1. CirSim.java (~6700 lines)
The main simulator class - orchestrates UI and coordinates with simulation engine.

**Responsibilities:**
- Handles user interactions (mouse, keyboard)
- Manages UI (menus, toolbars, scopes, canvas rendering)
- Circuit file I/O (save/load)
- Maintains list of circuit elements
- Coordinates with CircuitSimulationEngine for simulation execution
- Delegates matrix stamping to simulation engine

**Key Fields:**
```java
Vector<CircuitElm> elmList;              // All circuit elements
CircuitSimulationEngine simulationEngine; // NEW! Simulation engine
double circuitMatrix[][];                // The 'A' matrix (synced with engine)
double circuitRightSide[];               // The 'B' vector (synced with engine)
int circuitMatrixSize;                   // Size of matrix
boolean simRunning;                      // Simulation running state
```

#### 1.1 CircuitSimulationEngine.java (~600 lines) **NEW!**
The simulation engine class - handles pure circuit simulation logic.

**Responsibilities:**
- Builds and solves the MNA matrix
- Manages matrix stamping operations
- Handles timestep management and convergence
- Calculates node voltages and currents
- No UI dependencies - pure simulation logic

**Key Fields:**
```java
double circuitMatrix[][];          // The 'A' matrix
double circuitRightSide[];         // The 'B' vector
double nodeVoltages[];             // Solved node voltages
int circuitMatrixSize;             // Size of matrix
double timeStep;                   // Simulation timestep (seconds)
boolean converged;                 // Has iteration converged?
CircuitElm voltageSources[];       // Voltage source elements
```

**Key Methods:**
```java
void stampVoltageSource(int n1, int n2, int vs, double v);
void stampResistor(int n1, int n2, double r);
void stampMatrix(int i, int j, double x);
void stampCircuit();               // Populate the matrix
void runCircuit(boolean didAnalyze); // Execute simulation iterations
void applySolvedRightSide(double rs[]); // Apply solved voltages
```

#### 2. CircuitElm.java (~2500 lines)
Abstract base class for all circuit elements.

**Responsibilities:**
- Define interface for all elements
- Handle common functionality (drawing, node connections)
- Provide utility methods for subclasses

**Key Fields:**
```java
int x, y, x2, y2;                 // Element endpoints
Point point1, point2;             // Endpoints as Point objects
Point lead1, lead2;               // Wire stub endpoints
int nodes[];                      // Node indices in matrix
double volts[];                   // Voltage at each node
double current;                   // Current through element
int flags;                        // Bit flags for element properties
```

**Key Methods:**
```java
abstract void stamp();            // Add to MNA matrix (linear part)
abstract void doStep();           // Update matrix each timestep
abstract void draw(Graphics g);   // Render element
abstract int getPostCount();      // Number of connection points
abstract Point getPost(int n);    // Get connection point location
```

#### 3. Element Hierarchy

Over 200 element types organized in inheritance hierarchy:

```
CircuitElm (abstract base)
├── ResistorElm (passive)
├── CapacitorElm (passive, reactive)
├── InductorElm (passive, reactive)
├── VoltageElm (sources)
│   ├── DCVoltageElm
│   ├── ACVoltageElm
│   └── SquareWaveElm
├── CurrentElm (current sources)
├── DiodeElm (nonlinear)
├── TransistorElm (nonlinear, active)
│   ├── NTransistorElm
│   └── PTransistorElm
├── ChipElm (digital logic base)
│   ├── AndGateElm
│   ├── OrGateElm
│   ├── NandGateElm
│   └── (50+ logic gates and ICs)
└── CompositeElm (built from other elements)
    ├── OpAmpElm
    └── (various complex components)
```

---

## Main Program Loop

The simulation runs continuously in a loop that processes circuit changes and updates the display.

### Program Flow

```
Application Start
      ↓
   Initialize
      ↓
┌─────▼─────────┐
│  updateCircuit()  │ ← Main Loop (runs continuously)
└─────┬─────────┘
      │
      ├──→ Circuit Changed? ──→ Yes ──→ analyzeCircuit()
      │                                      ↓
      │                                 stampCircuit()
      │                                      ↓
      ├──────────────────────────────────────┘
      │
      ├──→ runCircuit() (simulate one timestep)
      │        │
      │        ├──→ Iteration Loop (for each timestep)
      │        │        │
      │        │        └──→ Subiteration Loop (until convergence)
      │        │                 │
      │        │                 ├──→ Call doStep() on all elements
      │        │                 ├──→ Solve matrix (lu_solve)
      │        │                 ├──→ Check convergence
      │        │                 └──→ Repeat if not converged
      │        │
      │        └──→ Update element states
      │
      ├──→ updateCircuitCanvas() (render graphics)
      │        │
      │        ├──→ Draw grid
      │        ├──→ Draw elements (call draw() on each)
      │        ├──→ Draw current animations
      │        └──→ Draw scopes
      │
      └──→ Process user input
           └──→ Handle mouse/keyboard events
```

### Detailed Loop Functions

#### updateCircuit()
```java
void updateCircuit() {
    // Main simulation loop
    
    // 1. Check if circuit needs reanalysis
    if (analyzeFlag) {
        analyzeCircuit();      // Build node list, check validity
        stampCircuit();        // Create MNA matrix
        analyzeFlag = false;
    }
    
    // 2. Run simulation for multiple timesteps per frame
    for (int iter = 0; iter < speedBar.getValue(); iter++) {
        runCircuit();          // Simulate one timestep
    }
    
    // 3. Update graphics
    updateCircuitCanvas();     // Render to screen
    
    // 4. Schedule next iteration
    scheduleNextUpdate();      // Continue loop
}
```

#### analyzeCircuit()
```java
void analyzeCircuit() {
    // Called when circuit topology changes
    
    // 1. Find all wires and group connected nodes
    calculateWireClosure();
    
    // 2. Assign node numbers to all connection points
    // Node 0 is always ground (reference voltage)
    int nodeCount = 0;
    for each element:
        for each post:
            if post not yet assigned a node:
                assign node number (nodeCount++)
    
    // 3. Find nodes not connected to ground
    findUnconnectedNodes();
    
    // 4. Count voltage sources and internal nodes
    // These require extra rows in matrix
    voltageSourceCount = 0;
    for each element:
        voltageSourceCount += element.getVoltageSourceCount();
        nodeCount += element.getInternalNodeCount();
    
    // 5. Calculate matrix size
    circuitMatrixSize = nodeCount + voltageSourceCount;
    
    // 6. Validate circuit (check for common errors)
    validateCircuit();  // Checks for voltage loops, etc.
    
    // 7. Prepare for matrix building
    circuitNeedsMap = true;  // Simplification needed
}
```

#### stampCircuit()
```java
void stampCircuit() {
    // Build the MNA matrix
    
    // 1. Allocate matrices
    circuitMatrix = new double[circuitMatrixSize][circuitMatrixSize];
    circuitRightSide = new double[circuitMatrixSize];
    
    // 2. Initialize to zero
    for (int i = 0; i < circuitMatrixSize; i++) {
        circuitRightSide[i] = 0;
        for (int j = 0; j < circuitMatrixSize; j++)
            circuitMatrix[i][j] = 0;
    }
    
    // 3. Have each element stamp its contribution
    for each element in circuit:
        element.stamp();        // Add linear component
    
    // 4. Connect unconnected nodes to ground
    connectUnconnectedNodes();  // Add large resistors
    
    // 5. Simplify matrix (remove trivial rows/columns)
    if (circuitNeedsMap) {
        simplifyMatrix();
        circuitNeedsMap = false;
    }
    
    // 6. If circuit is linear, do LU factorization now
    if (circuit is linear) {
        lu_factor(circuitMatrix);  // Only need to do this once
    }
}
```

#### runCircuit()
```java
void runCircuit() {
    // Simulate circuit for one timestep
    
    // Iteration loop - runs once per timestep
    for (int iter = 0; iter < maxIterations; iter++) {
        
        // Tell elements iteration is starting
        for each element:
            element.startIteration();
        
        // Subiteration loop - for convergence
        converged = true;
        int subiter;
        for (subiter = 0; subiter < maxSubIterations; subiter++) {
            
            // Have each element update matrix/right side
            for each element:
                element.doStep();
            
            // For nonlinear circuits, rebuild matrix each time
            if (circuit is nonlinear) {
                lu_factor(circuitMatrix);
            }
            
            // Solve matrix equation: X = A⁻¹B
            lu_solve(circuitMatrix, circuitRightSide, solution);
            
            // Copy solution to node voltages
            for each node:
                node.voltage = solution[node.index];
            
            // Copy solution to voltage source currents
            for each voltage source:
                source.current = solution[source.index];
            
            // Check if converged
            if (converged) break;
        }
        
        // Tell elements timestep is finished
        for each element:
            element.stepFinished();
        
        if (!converged) {
            // Circuit didn't converge - might need smaller timestep
            handleConvergenceFailure();
            break;
        }
    }
    
    // Advance simulation time
    t += timeStep;
}
```

---

## Circuit Element System

### Element Lifecycle

```
1. Creation
   ↓
2. setPoints() - calculate geometry
   ↓
3. allocNodes() - allocate node array
   ↓
4. stamp() - add linear component to matrix
   ↓
5. Loop:
   ├→ startIteration() - prepare for timestep
   ├→ doStep() - update matrix/right side (may loop for convergence)
   ├→ (matrix solved here)
   ├→ stepFinished() - finalize timestep
   └→ draw() - render element
```

### How Elements Work

#### Resistor Example

A resistor connects two nodes with resistance R.

**Stamp Method:**
```java
void stamp() {
    // Resistor from node a to node b with resistance R
    // Conductance G = 1/R
    // Current from a to b: I = (Va - Vb) * G
    
    int node_a = nodes[0];  // First node
    int node_b = nodes[1];  // Second node
    double G = 1.0 / resistance;
    
    // Add conductance to matrix
    // These represent Kirchhoff's Current Law at each node
    sim.stampResistor(node_a, node_b, G);
}

// In CirSim.java:
void stampResistor(int n1, int n2, double g) {
    // Current leaving node 1: I = (V1 - V2) * g
    // Current entering node 2: I = (V1 - V2) * g
    
    if (n1 != 0) {  // If not ground
        circuitMatrix[n1][n1] += g;   // Positive conductance term
        if (n2 != 0)
            circuitMatrix[n1][n2] -= g;  // Negative term for V2
    }
    
    if (n2 != 0) {  // If not ground
        circuitMatrix[n2][n2] += g;   // Positive conductance term
        if (n1 != 0)
            circuitMatrix[n2][n1] -= g;  // Negative term for V1
    }
}
```

**Draw Method:**
```java
void draw(Graphics g) {
    // Draw the resistor body
    g.setColor(needsHighlight() ? selectColor : lightGrayColor);
    
    // Draw resistor symbol (zigzag or rectangle based on style)
    if (euroResistor) {
        drawThickRectangle(point1, point2, width, height);
    } else {
        drawThickZigzag(point1, point2, segments);
    }
    
    // Draw connection posts
    drawPosts();
    
    // Draw current animation dots
    doDots();
    
    // Draw voltage drop indicator if showing volts
    if (sim.voltsCheckItem.getState()) {
        drawVoltageText(volts[0] - volts[1]);
    }
    
    // Update bounding box for mouse selection
    setBbox(point1, point2, padding);
}
```

#### Capacitor Example

A capacitor stores charge and resists voltage changes.

**Model:**
- Represented as current source parallel with resistor
- Resistor value proportional to 1/C (inverse capacitance)
- Current source value updates each timestep

**Stamp Method:**
```java
void stamp() {
    // Initial stamp - just the parallel resistor
    int node_a = nodes[0];
    int node_b = nodes[1];
    
    // Companion conductance (depends on integration method)
    double g = capacitance * 2 / timeStep;  // For trapezoidal
    
    sim.stampResistor(node_a, node_b, g);
}
```

**DoStep Method:**
```java
void doStep() {
    // Called each timestep to update current source
    
    double v = volts[0] - volts[1];  // Voltage across capacitor
    
    // Calculate new current using integration
    // Trapezoidal: I_new = g*V_new + g*V_old + I_old
    double g = capacitance * 2 / timeStep;
    double i_companion = v * g + current;
    
    // Stamp current source into right side
    sim.stampCurrentSource(nodes[0], nodes[1], i_companion);
    
    // Update current for next timestep
    current = v * g - current;
}
```

#### Inductor Example

An inductor stores magnetic energy and resists current changes.

**Model:**
- Represented as current source parallel with resistor
- Resistor value proportional to L (inductance)
- Current source value updates each timestep

**Stamp Method:**
```java
void stamp() {
    // Parallel resistor representing resistance to di/dt
    double g = timeStep / (inductance * 2);  // For trapezoidal
    
    sim.stampResistor(nodes[0], nodes[1], g);
}
```

**DoStep Method:**
```java
void doStep() {
    double v = volts[0] - volts[1];
    
    // Calculate new current using integration
    // Trapezoidal: I_new = I_old + (V_new + V_old) * g
    double g = timeStep / (inductance * 2);
    double i_new = current + (v + compResistance) * g;
    
    // Stamp current source
    double i_companion = i_new - v * g;
    sim.stampCurrentSource(nodes[0], nodes[1], i_companion);
    
    // Save values for next timestep
    current = i_new;
    compResistance = v;
}
```

#### Diode Example (Nonlinear)

A diode is nonlinear: current is exponential function of voltage.

**Model:**
- Linearize around operating point using tangent line
- Tangent line = resistance + current source
- Iterate to find correct operating point

**DoStep Method:**
```java
void doStep() {
    double v = volts[0] - volts[1];
    
    // Shockley diode equation: I = Is * (exp(V / Vt) - 1)
    // where Vt = thermal voltage (~26mV at room temp)
    
    // Limit voltage change to avoid huge currents
    if (v > maxVoltageStep) v = maxVoltageStep;
    if (v < -maxVoltageStep) v = -maxVoltageStep;
    
    // Calculate current and derivative at this voltage
    double i = saturationCurrent * (Math.exp(v / thermalVoltage) - 1);
    double dI_dV = saturationCurrent * Math.exp(v / thermalVoltage) / thermalVoltage;
    
    // Create tangent line: I = dI_dV * V + I_offset
    // This is conductance dI_dV in parallel with current source I_offset
    double g = dI_dV;
    double i_offset = i - dI_dV * v;
    
    // Stamp linearized model
    sim.stampResistor(nodes[0], nodes[1], g);
    sim.stampCurrentSource(nodes[0], nodes[1], i_offset);
    
    // Check for convergence
    if (Math.abs(i - lastCurrent) > convergenceThreshold) {
        sim.converged = false;  // Need another iteration
    }
    
    lastCurrent = i;
    current = i;
}
```

#### Voltage Source Example

Voltage sources require an extra row/column in the matrix.

**Stamp Method:**
```java
void stamp() {
    // Voltage source from node a to node b
    // Constraint: Vb - Va = Vs
    // Also need to solve for current through source
    
    int node_a = nodes[0];
    int node_b = nodes[1];
    int vs_row = voltSource;  // Extra row for this source
    
    sim.stampVoltageSource(node_a, node_b, vs_row, voltage);
}

// In CirSim.java:
void stampVoltageSource(int n1, int n2, int vs, double v) {
    int vn = nodeCount + vs;  // Row number for voltage source
    
    // Constraint equation: Vn2 - Vn1 = v
    if (n1 != 0)
        circuitMatrix[vn][n1] = -1;  // -V1
    if (n2 != 0)
        circuitMatrix[vn][n2] = 1;   // +V2
    circuitRightSide[vn] = v;        // = Vs
    
    // Current flow through voltage source
    if (n1 != 0)
        circuitMatrix[n1][vn] = 1;   // Current from node 1
    if (n2 != 0)
        circuitMatrix[n2][vn] = -1;  // Current into node 2
}
```

---

## Modified Nodal Analysis (MNA)

### Complete Example

Consider this simple circuit:
```
    R1=100Ω      R2=200Ω
  ┌────────┬────────┬────┐
  │        │        │    │
  V=10V   GND    R3=150Ω │
  │               │      │
  └───────────────┴──────┘
```

**Step 1: Number the nodes**
- Node 0: Ground (GND)
- Node 1: Between V and R1
- Node 2: Between R1 and R2
- Node 3: Between R2 and R3

**Step 2: Build the matrix**

For voltage source:
- Need extra row/column (row 4) for current through V

For resistors:
- G1 = 1/100 = 0.01 S
- G2 = 1/200 = 0.005 S
- G3 = 1/150 = 0.00667 S

Matrix A (5x5, including voltage source):
```
     V1      V2      V3      I_V
[  0.01      0       0      -1   ]  Node 1
[  -0.01    0.015   -0.005   0   ]  Node 2
[   0     -0.005   0.01167   0   ]  Node 3
[  -1       0       0        0   ]  Voltage source
```

Right side B:
```
[  0  ]  Node 1 (no current source)
[  0  ]  Node 2
[  0  ]  Node 3
[ 10  ]  Voltage source = 10V
```

**Step 3: Solve X = A⁻¹B**

Solution X:
```
[ V1 = 10   ]  Voltage at node 1
[ V2 = 5.0  ]  Voltage at node 2
[ V3 = 1.43 ]  Voltage at node 3
[ I_V = 0.1 ]  Current through voltage source
```

**Step 4: Calculate element values**
- Current through R1: (V1-V2)/100 = (10-5)/100 = 0.05 A
- Current through R2: (V2-V3)/200 = (5-1.43)/200 = 0.0179 A
- Current through R3: V3/150 = 1.43/150 = 0.0095 A

### Why MNA is Powerful

1. **Systematic**: Same process for any circuit
2. **Efficient**: Matrix operations are well-optimized
3. **Flexible**: Handles linear and nonlinear elements
4. **Accurate**: Numerical precision of computer arithmetic

---

## Rendering System

### Graphics Architecture

```
Canvas (HTML5)
    ↓
Context2d (2D drawing context)
    ↓
CirSim.updateCircuitCanvas()
    ↓
For each element:
    element.draw(Graphics g)
        ↓
        Draw element body
        Draw connection posts
        Draw current animation
        Draw voltage/current labels
```

### Drawing Pipeline

```java
void updateCircuitCanvas() {
    // 1. Clear canvas
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // 2. Apply transform (for zooming/panning)
    context.setTransform(transform);
    
    // 3. Draw grid
    if (gridCheckItem.getState()) {
        drawGrid();
    }
    
    // 4. Draw all elements
    for (CircuitElm element : elmList) {
        element.draw(context);
    }
    
    // 5. Draw selection rectangle
    if (selecting) {
        drawSelectionRect();
    }
    
    // 6. Draw scopes
    for (Scope scope : scopes) {
        scope.draw();
    }
    
    // 7. Draw mouse cursor crosshairs
    if (crossHairCheckItem.getState()) {
        drawCrossHairs();
    }
}
```

### Current Animation

The flowing current is animated using moving dots.

```java
void doDots() {
    // Calculate phase of dot animation
    updateDotCount(current, curcount);
    
    // Draw dots along element path
    drawDots(lead1, lead2, curcount);
}

void drawDots(Point p1, Point p2, double pos) {
    // Calculate number of dots based on length
    int numDots = (int)(distance(p1, p2) / dotSpacing);
    
    // Draw each dot
    for (int i = 0; i < numDots; i++) {
        // Calculate dot position along line
        double t = (i + pos) / numDots;
        int x = (int)(p1.x + (p2.x - p1.x) * t);
        int y = (int)(p1.y + (p2.y - p1.y) * t);
        
        // Draw dot with brightness based on current
        double brightness = Math.abs(current) * currentMult;
        Color dotColor = interpolateColor(neutralColor, currentColor, brightness);
        
        graphics.setColor(dotColor);
        graphics.fillOval(x-2, y-2, 4, 4);
    }
}
```

### Color Coding

Elements are color-coded to show voltage:

```java
void setVoltageColor(double v) {
    // Map voltage to color scale
    // -voltageRange (red) -> 0 (gray) -> +voltageRange (green)
    
    int index = (int)((v / voltageRange + 1) * colorScaleCount / 2);
    
    // Clamp to valid range
    if (index < 0) index = 0;
    if (index >= colorScaleCount) index = colorScaleCount - 1;
    
    graphics.setColor(colorScale[index]);
}
```

---

## Migration to ReactJS

### Overall Strategy

The GWT/Java application can be recreated in ReactJS using modern web technologies.

### Architecture Mapping

| Java/GWT Component | ReactJS Equivalent | Purpose |
|--------------------|-------------------|---------|
| CirSim.java | App.tsx + CircuitSimulator.ts | Main application logic |
| CircuitElm.java | CircuitElement.ts (base class) | Element interface |
| Element subclasses | Element implementations | Specific components |
| GWT Canvas | HTML5 Canvas + React ref | Drawing surface |
| GWT Widgets | React components | UI elements |
| Vector<CircuitElm> | Array of elements | Circuit storage |
| Matrix operations | math.js or numeric.js | Linear algebra |

### Project Structure

```
circuit-simulator-react/
├── src/
│   ├── components/          # React UI components
│   │   ├── App.tsx
│   │   ├── Canvas.tsx
│   │   ├── Toolbar.tsx
│   │   ├── Menu.tsx
│   │   └── Scope.tsx
│   ├── simulator/           # Core simulation engine
│   │   ├── CircuitSimulator.ts
│   │   ├── MatrixSolver.ts
│   │   ├── CircuitAnalyzer.ts
│   │   └── TimeStepManager.ts
│   ├── elements/            # Circuit elements
│   │   ├── CircuitElement.ts (base class)
│   │   ├── Resistor.ts
│   │   ├── Capacitor.ts
│   │   ├── Inductor.ts
│   │   ├── VoltageSource.ts
│   │   ├── Diode.ts
│   │   └── ... (200+ elements)
│   ├── rendering/           # Graphics system
│   │   ├── CanvasRenderer.ts
│   │   ├── ElementDrawer.ts
│   │   └── ColorScheme.ts
│   ├── utils/               # Utilities
│   │   ├── Point.ts
│   │   ├── Rectangle.ts
│   │   └── MathUtils.ts
│   └── types/               # TypeScript types
│       └── index.ts
├── package.json
└── tsconfig.json
```

### Tech Stack for React Version

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "mathjs": "^11.11.0",        // Matrix operations
    "zustand": "^4.4.0",         // State management
    "react-konva": "^18.2.0",    // Alternative: Canvas library
    "tailwindcss": "^3.3.0"      // Styling
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "vite": "^4.4.0"             // Build tool
  }
}
```

### Core Code Examples

#### 1. CircuitElement Base Class (TypeScript)

```typescript
// src/elements/CircuitElement.ts

export abstract class CircuitElement {
  // Position
  x: number;
  y: number;
  x2: number;
  y2: number;
  
  // Electrical properties
  nodes: number[];      // Node indices in matrix
  volts: number[];      // Voltage at each node
  current: number;      // Current through element
  
  // Visual properties
  selected: boolean;
  boundingBox: Rectangle;
  
  constructor(x: number, y: number, x2: number, y2: number) {
    this.x = x;
    this.y = y;
    this.x2 = x2;
    this.y2 = y2;
    this.nodes = [];
    this.volts = [];
    this.current = 0;
    this.selected = false;
  }
  
  // Methods to implement in subclasses
  abstract getPostCount(): number;
  abstract getPost(n: number): Point;
  abstract stamp(sim: CircuitSimulator): void;
  abstract doStep(sim: CircuitSimulator): void;
  abstract draw(ctx: CanvasRenderingContext2D): void;
  abstract getDumpType(): number;
  
  // Common methods
  setPoints(): void {
    // Calculate geometry
    const dx = this.x2 - this.x;
    const dy = this.y2 - this.y;
    const dn = Math.sqrt(dx * dx + dy * dy);
    // ... setup points
  }
  
  allocNodes(): void {
    this.nodes = new Array(this.getPostCount());
    this.volts = new Array(this.getPostCount());
  }
  
  isInBoundingBox(x: number, y: number): boolean {
    return this.boundingBox.contains(x, y);
  }
}
```

#### 2. Resistor Implementation

```typescript
// src/elements/Resistor.ts

export class Resistor extends CircuitElement {
  resistance: number;  // Ohms
  
  constructor(x: number, y: number, x2: number, y2: number, resistance: number = 1000) {
    super(x, y, x2, y2);
    this.resistance = resistance;
  }
  
  getPostCount(): number {
    return 2;  // Two-terminal device
  }
  
  getPost(n: number): Point {
    return n === 0 ? new Point(this.x, this.y) : new Point(this.x2, this.y2);
  }
  
  stamp(sim: CircuitSimulator): void {
    // Add conductance to matrix
    const g = 1.0 / this.resistance;
    sim.stampResistor(this.nodes[0], this.nodes[1], g);
  }
  
  doStep(sim: CircuitSimulator): void {
    // Resistor is linear, nothing to do here
    // Current calculated from voltage:
    this.current = (this.volts[0] - this.volts[1]) / this.resistance;
  }
  
  draw(ctx: CanvasRenderingContext2D): void {
    ctx.save();
    
    // Set color
    ctx.strokeStyle = this.selected ? '#00ffff' : '#ffffff';
    ctx.lineWidth = 2;
    
    // Draw resistor body (zigzag)
    ctx.beginPath();
    ctx.moveTo(this.x, this.y);
    
    // Draw zigzag pattern
    const segments = 6;
    const width = 8;
    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      const px = this.x + (this.x2 - this.x) * t;
      const py = this.y + (this.y2 - this.y) * t;
      const offset = (i % 2 === 0 ? 1 : -1) * width;
      ctx.lineTo(px + offset, py);
    }
    
    ctx.stroke();
    
    // Draw current animation dots
    this.drawDots(ctx);
    
    // Draw value label
    ctx.fillStyle = '#ffffff';
    ctx.font = '12px Arial';
    ctx.fillText(this.formatResistance(), (this.x + this.x2) / 2, (this.y + this.y2) / 2 - 10);
    
    ctx.restore();
  }
  
  drawDots(ctx: CanvasRenderingContext2D): void {
    // Animate current flow
    const phase = Date.now() / 1000;  // Animation phase
    const spacing = 20;
    const length = Math.sqrt((this.x2 - this.x) ** 2 + (this.y2 - this.y) ** 2);
    const numDots = Math.floor(length / spacing);
    
    for (let i = 0; i < numDots; i++) {
      const t = ((i + phase * Math.abs(this.current)) % numDots) / numDots;
      const x = this.x + (this.x2 - this.x) * t;
      const y = this.y + (this.y2 - this.y) * t;
      
      ctx.fillStyle = '#ffff00';  // Yellow dots
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
  
  formatResistance(): string {
    if (this.resistance >= 1e6) return `${(this.resistance / 1e6).toFixed(1)}MΩ`;
    if (this.resistance >= 1e3) return `${(this.resistance / 1e3).toFixed(1)}kΩ`;
    return `${this.resistance.toFixed(1)}Ω`;
  }
  
  getDumpType(): number {
    return ElementType.RESISTOR;
  }
}
```

#### 3. Circuit Simulator Core

```typescript
// src/simulator/CircuitSimulator.ts

export class CircuitSimulator {
  elements: CircuitElement[];
  
  // Matrix variables
  circuitMatrix: number[][];
  circuitRightSide: number[];
  solution: number[];
  matrixSize: number;
  
  // Simulation parameters
  timeStep: number;
  currentTime: number;
  converged: boolean;
  
  // Flags
  analyzeFlag: boolean;
  isLinear: boolean;
  
  constructor() {
    this.elements = [];
    this.timeStep = 5e-6;  // 5 microseconds
    this.currentTime = 0;
    this.analyzeFlag = true;
  }
  
  addElement(element: CircuitElement): void {
    this.elements.push(element);
    this.analyzeFlag = true;  // Need to reanalyze
  }
  
  removeElement(element: CircuitElement): void {
    const index = this.elements.indexOf(element);
    if (index >= 0) {
      this.elements.splice(index, 1);
      this.analyzeFlag = true;
    }
  }
  
  simulate(): void {
    // Main simulation step
    
    // Reanalyze if circuit changed
    if (this.analyzeFlag) {
      this.analyzeCircuit();
      this.stampCircuit();
      this.analyzeFlag = false;
    }
    
    // Run simulation timesteps
    this.runCircuit();
  }
  
  analyzeCircuit(): void {
    // Assign node numbers to all connection points
    let nodeCount = 0;
    const nodeMap = new Map<string, number>();
    
    // Node 0 is always ground
    nodeMap.set('0,0', 0);
    
    // Find all unique nodes
    for (const element of this.elements) {
      for (let i = 0; i < element.getPostCount(); i++) {
        const post = element.getPost(i);
        const key = `${post.x},${post.y}`;
        
        if (!nodeMap.has(key)) {
          nodeMap.set(key, ++nodeCount);
        }
        
        element.nodes[i] = nodeMap.get(key)!;
      }
    }
    
    // Count voltage sources (need extra rows)
    let voltageSourceCount = 0;
    for (const element of this.elements) {
      if (element instanceof VoltageSource) {
        element.voltageSourceIndex = voltageSourceCount++;
      }
    }
    
    // Calculate matrix size
    this.matrixSize = nodeCount + voltageSourceCount;
    
    // Check if circuit is linear
    this.isLinear = this.elements.every(e => e.isLinear());
  }
  
  stampCircuit(): void {
    // Allocate matrices
    this.circuitMatrix = Array(this.matrixSize).fill(null)
      .map(() => Array(this.matrixSize).fill(0));
    this.circuitRightSide = Array(this.matrixSize).fill(0);
    this.solution = Array(this.matrixSize).fill(0);
    
    // Have each element stamp its contribution
    for (const element of this.elements) {
      element.stamp(this);
    }
    
    // For linear circuits, factor once
    if (this.isLinear) {
      this.luFactor(this.circuitMatrix);
    }
  }
  
  runCircuit(): void {
    const maxSubIterations = 5000;
    
    // Subiteration loop for convergence
    for (let subiter = 0; subiter < maxSubIterations; subiter++) {
      this.converged = true;
      
      // Reset right side
      this.circuitRightSide.fill(0);
      
      // Have each element update matrix/right side
      for (const element of this.elements) {
        element.doStep(this);
      }
      
      // For nonlinear circuits, refactor each iteration
      if (!this.isLinear) {
        this.luFactor(this.circuitMatrix);
      }
      
      // Solve matrix equation
      this.luSolve(this.circuitMatrix, this.circuitRightSide, this.solution);
      
      // Copy solution to element voltages
      for (const element of this.elements) {
        for (let i = 0; i < element.nodes.length; i++) {
          element.volts[i] = this.solution[element.nodes[i]];
        }
      }
      
      // Check convergence
      if (this.converged) break;
    }
    
    // Advance time
    this.currentTime += this.timeStep;
  }
  
  // Matrix stamping methods
  stampResistor(node1: number, node2: number, g: number): void {
    if (node1 !== 0) {
      this.circuitMatrix[node1][node1] += g;
      if (node2 !== 0)
        this.circuitMatrix[node1][node2] -= g;
    }
    if (node2 !== 0) {
      this.circuitMatrix[node2][node2] += g;
      if (node1 !== 0)
        this.circuitMatrix[node2][node1] -= g;
    }
  }
  
  stampCurrentSource(node1: number, node2: number, i: number): void {
    if (node1 !== 0)
      this.circuitRightSide[node1] -= i;
    if (node2 !== 0)
      this.circuitRightSide[node2] += i;
  }
  
  stampVoltageSource(node1: number, node2: number, vsIndex: number, v: number): void {
    const vn = this.matrixSize - 1 - vsIndex;  // Voltage source row
    
    if (node1 !== 0)
      this.circuitMatrix[vn][node1] = -1;
    if (node2 !== 0)
      this.circuitMatrix[vn][node2] = 1;
    
    this.circuitRightSide[vn] = v;
    
    if (node1 !== 0)
      this.circuitMatrix[node1][vn] = 1;
    if (node2 !== 0)
      this.circuitMatrix[node2][vn] = -1;
  }
  
  // LU decomposition and solve
  luFactor(matrix: number[][]): void {
    // Implementation of LU factorization
    // See next section for complete algorithm
  }
  
  luSolve(matrix: number[][], rhs: number[], solution: number[]): void {
    // Forward substitution then backward substitution
    // See next section for complete algorithm
  }
}
```

#### 4. React Canvas Component

```typescript
// src/components/Canvas.tsx

import React, { useRef, useEffect } from 'react';
import { CircuitSimulator } from '../simulator/CircuitSimulator';

interface CanvasProps {
  simulator: CircuitSimulator;
  width: number;
  height: number;
}

export const Canvas: React.FC<CanvasProps> = ({ simulator, width, height }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Main animation loop
    const animate = () => {
      // Simulate
      simulator.simulate();
      
      // Clear canvas
      ctx.clearRect(0, 0, width, height);
      
      // Draw grid
      drawGrid(ctx, width, height);
      
      // Draw all elements
      for (const element of simulator.elements) {
        element.draw(ctx);
      }
      
      // Continue animation
      animationFrameRef.current = requestAnimationFrame(animate);
    };
    
    animate();
    
    // Cleanup
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [simulator, width, height]);
  
  const drawGrid = (ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.strokeStyle = '#333333';
    ctx.lineWidth = 0.5;
    
    const gridSize = 20;
    
    // Vertical lines
    for (let x = 0; x < w; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    
    // Horizontal lines
    for (let y = 0; y < h; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
  };
  
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Find clicked element
    for (const element of simulator.elements) {
      if (element.isInBoundingBox(x, y)) {
        element.selected = !element.selected;
        break;
      }
    }
  };
  
  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onMouseDown={handleMouseDown}
      style={{ border: '1px solid #444', background: '#000' }}
    />
  );
};
```

#### 5. Main App Component

```typescript
// src/components/App.tsx

import React, { useState } from 'react';
import { Canvas } from './Canvas';
import { Toolbar } from './Toolbar';
import { CircuitSimulator } from '../simulator/CircuitSimulator';
import { Resistor } from '../elements/Resistor';
import { VoltageSource } from '../elements/VoltageSource';

export const App: React.FC = () => {
  const [simulator] = useState(() => {
    const sim = new CircuitSimulator();
    
    // Add example circuit
    const voltage = new VoltageSource(100, 100, 100, 200, 10);  // 10V
    const resistor = new Resistor(100, 200, 200, 200, 1000);    // 1kΩ
    
    sim.addElement(voltage);
    sim.addElement(resistor);
    
    return sim;
  });
  
  const handleAddResistor = () => {
    const resistor = new Resistor(200, 100, 300, 100, 1000);
    simulator.addElement(resistor);
  };
  
  return (
    <div className="app">
      <Toolbar onAddResistor={handleAddResistor} />
      <Canvas simulator={simulator} width={800} height={600} />
    </div>
  );
};
```

---

## Key Algorithms with Pseudocode

### 1. LU Decomposition

LU decomposition factorizes matrix A into lower (L) and upper (U) triangular matrices.

```
Algorithm: LU_Factor(A, n)
Input: Matrix A of size n×n
Output: Matrix A modified to contain L and U

for k = 0 to n-1:
    # Find pivot (largest element in column k)
    max_val = |A[k][k]|
    pivot_row = k
    
    for i = k+1 to n-1:
        if |A[i][k]| > max_val:
            max_val = |A[i][k]|
            pivot_row = i
    
    # Swap rows if needed
    if pivot_row != k:
        swap rows k and pivot_row in A
    
    # Check for singular matrix
    if A[k][k] == 0:
        error "Matrix is singular"
    
    # Eliminate column k
    for i = k+1 to n-1:
        multiplier = A[i][k] / A[k][k]
        A[i][k] = multiplier  # Store in L
        
        for j = k+1 to n-1:
            A[i][j] -= multiplier * A[k][j]

# Now A contains:
# - L below diagonal (multipliers)
# - U on and above diagonal
```

### 2. LU Solve

After factorization, solve Ax = b by solving Ly = b then Ux = y.

```
Algorithm: LU_Solve(A, b, x, n)
Input: Factored matrix A, right side b, size n
Output: Solution x

# Forward substitution: Ly = b
for i = 0 to n-1:
    sum = b[i]
    for j = 0 to i-1:
        sum -= A[i][j] * x[j]
    x[i] = sum  # L has 1's on diagonal

# Backward substitution: Ux = y
for i = n-1 down to 0:
    sum = x[i]
    for j = i+1 to n-1:
        sum -= A[i][j] * x[j]
    x[i] = sum / A[i][i]
```

### 3. Circuit Analysis

```
Algorithm: AnalyzeCircuit()
Output: Node assignments, voltage source count

# 1. Find connected wire groups
CalculateWireClosure()

# 2. Assign node numbers
nodeCount = 0
nodeMap = empty map

for each element in circuit:
    for each post in element:
        position = post.getPosition()
        
        if position not in nodeMap:
            nodeMap[position] = nodeCount
            nodeCount++
        
        element.nodes[post_index] = nodeMap[position]

# 3. Count voltage sources
vsCount = 0
for each element in circuit:
    if element is VoltageSource:
        element.vsIndex = vsCount
        vsCount++

# 4. Calculate matrix size
matrixSize = nodeCount + vsCount

return nodeCount, vsCount
```

### 4. Matrix Stamping

```
Algorithm: StampCircuit()
Output: Filled matrix A and vector b

# Allocate matrices
A = zero matrix of size matrixSize × matrixSize
b = zero vector of size matrixSize

# Have each element add its contribution
for each element in circuit:
    element.stamp(A, b)

# Connect unconnected nodes to ground
for each node:
    if node is unconnected:
        # Add large resistor to ground
        stampResistor(node, 0, 1e-12)  # Very small conductance
```

### 5. Timestep Simulation

```
Algorithm: RunCircuit()
Modifies: Element voltages and currents

maxIterations = 5000
converged = false

for iteration = 1 to maxIterations:
    converged = true
    
    # Reset right side
    b = zero vector
    
    # Update matrix for nonlinear elements
    for each element in circuit:
        element.doStep()  # May modify A and b
        # May also set converged = false
    
    # Refactor if nonlinear
    if circuit is nonlinear:
        LU_Factor(A)
    
    # Solve
    LU_Solve(A, b, x)
    
    # Copy voltages to elements
    for each element in circuit:
        for each node in element:
            element.volts[node] = x[element.nodes[node]]
    
    if converged:
        break

# Update time
time += timeStep
```

### 6. Nonlinear Element Iteration (Diode Example)

```
Algorithm: DiodeDoStep()
Modifies: Matrix A, vector b, converged flag

# Get voltage across diode
v = volts[anode] - volts[cathode]

# Limit voltage change
if v > maxStep:
    v = maxStep
if v < -maxStep:
    v = -maxStep

# Calculate current using Shockley equation
# I = Is * (exp(V/Vt) - 1)
i = satCurrent * (exp(v / thermalVoltage) - 1)

# Calculate derivative (conductance at this point)
g = satCurrent * exp(v / thermalVoltage) / thermalVoltage

# Linearize: create tangent line
# I = g*V + i_offset
i_offset = i - g * v

# Stamp linearized model
stampResistor(anode, cathode, g)
stampCurrentSource(anode, cathode, i_offset)

# Check convergence
if |i - lastCurrent| > threshold:
    converged = false

lastCurrent = i
```

### 7. Capacitor Integration

```
Algorithm: CapacitorDoStep()
Uses: Trapezoidal integration

# Get voltage
v = volts[0] - volts[1]

# Companion conductance for trapezoidal
g = capacitance * 2 / timeStep

# Companion current source
# Trapezoidal: I_new = g*V_new + g*V_old + I_old
i_companion = v * g + current

# Stamp
stampResistor(node1, node2, g)
stampCurrentSource(node1, node2, i_companion)

# Update for next timestep
current = v * g - current
```

### 8. Wire Current Calculation

```
Algorithm: CalculateWireCurrent(wire)
Output: Current through wire

# Sum currents from all connected elements
current = 0

for each element connected to wire:
    # Get current entering wire from this element
    i = element.getCurrentIntoNode(wireNode)
    current += i

return current
```

---

## Summary

### What Makes This Simulator Work

1. **Mathematical Foundation**: Modified Nodal Analysis provides systematic circuit analysis
2. **Numerical Methods**: LU decomposition efficiently solves large matrix equations
3. **Integration**: Trapezoidal/backward Euler methods handle time-varying elements
4. **Linearization**: Newton-Raphson iteration handles nonlinear devices
5. **Animation**: Real-time rendering shows circuit behavior visually

### Key Insights for Migration

1. **Separation of Concerns**: Keep simulation engine separate from UI
2. **Matrix Library**: Use a proven library (math.js) rather than reimplementing
3. **Element Architecture**: Abstract base class with consistent interface
4. **Performance**: Consider Web Workers for simulation in separate thread
5. **State Management**: Use Zustand or Redux for managing circuit state
6. **Canvas Rendering**: Direct Canvas API or library like Konva
7. **TypeScript**: Type safety prevents many bugs in complex system

### Performance Considerations

- **Matrix Size**: O(n³) complexity - keep matrix small via simplification
- **Animation**: Use requestAnimationFrame for smooth 60fps rendering
- **Web Workers**: Run simulation in background thread
- **Canvas Optimization**: Only redraw changed elements
- **Memory**: Reuse arrays rather than allocating each frame

### Next Steps for ReactJS Implementation

1. Set up React + TypeScript project with Vite
2. Implement core matrix solver using math.js
3. Create CircuitElement base class
4. Implement basic elements (R, L, C, voltage source)
5. Build CircuitSimulator core
6. Create Canvas rendering component
7. Add mouse interaction for placing elements
8. Implement toolbar and menus
9. Add save/load functionality
10. Gradually add more element types

---

## Additional Resources

- **Original Theory**: "Electronic Circuit & System Simulation Methods" by Pillage et al.
- **MNA Tutorial**: https://lpsa.swarthmore.edu/Systems/Electrical/mna/MNA1.html
- **CircuitJS1 Source**: https://github.com/pfalstad/circuitjs1
- **LU Decomposition**: Numerical Recipes or Wikipedia
- **React Canvas**: MDN Canvas Tutorial
- **Matrix Libraries**: math.js documentation

This documentation provides a complete foundation for understanding and recreating the CircuitJS1 simulator in any modern framework.
