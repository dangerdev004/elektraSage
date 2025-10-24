# Quick Start Guide - Build Circuit Simulator in ReactJS

This guide will help you build a working circuit simulator from scratch in under an hour.

## Table of Contents
1. [Setup (5 minutes)](#setup)
2. [Basic Implementation (20 minutes)](#basic-implementation)
3. [Adding Components (15 minutes)](#adding-components)
4. [User Interface (15 minutes)](#user-interface)
5. [Testing (5 minutes)](#testing)

---

## Setup

### Step 1: Create Project

```bash
# Create new React + TypeScript project
npm create vite@latest circuit-simulator -- --template react-ts
cd circuit-simulator

# Install dependencies
npm install
npm install mathjs zustand

# Start development server
npm run dev
```

### Step 2: Create Project Structure

```bash
mkdir -p src/{simulator/{core,elements/{base,passive,sources}},components/{Canvas,Toolbar,Menu},utils,store}
```

---

## Basic Implementation

### Step 3: Create Utility Classes (5 minutes)

Create `src/utils/Point.ts`:

```typescript
export class Point {
  constructor(public x: number = 0, public y: number = 0) {}
  
  distance(other: Point): number {
    return Math.sqrt((this.x - other.x) ** 2 + (this.y - other.y) ** 2);
  }
  
  clone(): Point {
    return new Point(this.x, this.y);
  }
}
```

Create `src/utils/Rectangle.ts`:

```typescript
import { Point } from './Point';

export class Rectangle {
  constructor(
    public x: number,
    public y: number,
    public width: number,
    public height: number
  ) {}
  
  static fromPoints(p1: Point, p2: Point, padding: number = 5): Rectangle {
    const x = Math.min(p1.x, p2.x) - padding;
    const y = Math.min(p1.y, p2.y) - padding;
    const width = Math.abs(p1.x - p2.x) + 2 * padding;
    const height = Math.abs(p1.y - p2.y) + 2 * padding;
    return new Rectangle(x, y, width, height);
  }
  
  contains(x: number, y: number): boolean {
    return x >= this.x && x <= this.x + this.width &&
           y >= this.y && y <= this.y + this.height;
  }
}
```

### Step 4: Create Matrix Solver (5 minutes)

Create `src/simulator/core/MatrixSolver.ts`:

```typescript
export class MatrixSolver {
  private permutation: number[] = [];

  luFactor(matrix: number[][]): boolean {
    const n = matrix.length;
    this.permutation = Array.from({ length: n }, (_, i) => i);

    for (let k = 0; k < n; k++) {
      let maxVal = Math.abs(matrix[k][k]);
      let pivotRow = k;

      for (let i = k + 1; i < n; i++) {
        const val = Math.abs(matrix[i][k]);
        if (val > maxVal) {
          maxVal = val;
          pivotRow = i;
        }
      }

      if (maxVal < 1e-20) return false;

      if (pivotRow !== k) {
        [matrix[k], matrix[pivotRow]] = [matrix[pivotRow], matrix[k]];
        [this.permutation[k], this.permutation[pivotRow]] = 
          [this.permutation[pivotRow], this.permutation[k]];
      }

      for (let i = k + 1; i < n; i++) {
        const multiplier = matrix[i][k] / matrix[k][k];
        matrix[i][k] = multiplier;
        for (let j = k + 1; j < n; j++) {
          matrix[i][j] -= multiplier * matrix[k][j];
        }
      }
    }
    return true;
  }

  luSolve(matrix: number[][], rhs: number[], solution: number[]): void {
    const n = matrix.length;
    const y = new Array(n);

    for (let i = 0; i < n; i++) {
      y[i] = rhs[this.permutation[i]];
    }

    for (let i = 0; i < n; i++) {
      let sum = y[i];
      for (let j = 0; j < i; j++) {
        sum -= matrix[i][j] * y[j];
      }
      y[i] = sum;
    }

    for (let i = n - 1; i >= 0; i--) {
      let sum = y[i];
      for (let j = i + 1; j < n; j++) {
        sum -= matrix[i][j] * solution[j];
      }
      solution[i] = sum / matrix[i][i];
    }
  }
}
```

### Step 5: Create Circuit Element Base (5 minutes)

Create `src/simulator/elements/base/CircuitElement.ts`:

```typescript
import { Point } from '../../../utils/Point';
import { Rectangle } from '../../../utils/Rectangle';

export abstract class CircuitElement {
  x: number; y: number; x2: number; y2: number;
  nodes: number[] = [];
  volts: number[] = [];
  current: number = 0;
  selected: boolean = false;
  boundingBox: Rectangle;

  constructor(x: number, y: number, x2: number, y2: number) {
    this.x = x; this.y = y; this.x2 = x2; this.y2 = y2;
    this.boundingBox = new Rectangle(0, 0, 0, 0);
  }

  abstract draw(ctx: CanvasRenderingContext2D): void;
  abstract stamp(sim: any): void;
  
  getPostCount(): number { return 2; }
  getPost(n: number): Point {
    return n === 0 ? new Point(this.x, this.y) : new Point(this.x2, this.y2);
  }

  allocNodes(): void {
    this.nodes = new Array(this.getPostCount()).fill(-1);
    this.volts = new Array(this.getPostCount()).fill(0);
  }

  isInBoundingBox(x: number, y: number): boolean {
    return this.boundingBox.contains(x, y);
  }
}
```

### Step 6: Create Circuit Simulator Core (5 minutes)

Create `src/simulator/core/CircuitSimulator.ts`:

```typescript
import { CircuitElement } from '../elements/base/CircuitElement';
import { MatrixSolver } from './MatrixSolver';
import { Point } from '../../utils/Point';

export class CircuitSimulator {
  elements: CircuitElement[] = [];
  private matrixSolver = new MatrixSolver();
  circuitMatrix: number[][] = [];
  circuitRightSide: number[] = [];
  private solution: number[] = [];
  matrixSize: number = 0;
  timeStep: number = 5e-6;
  currentTime: number = 0;
  private nodeMap = new Map<string, number>();
  private nodeCount: number = 0;

  addElement(element: CircuitElement): void {
    this.elements.push(element);
    this.analyze();
  }

  removeElement(element: CircuitElement): void {
    const index = this.elements.indexOf(element);
    if (index >= 0) {
      this.elements.splice(index, 1);
      this.analyze();
    }
  }

  simulate(): void {
    if (this.elements.length === 0) return;
    
    // Reset right side
    this.circuitRightSide.fill(0);
    
    // Update elements
    for (const element of this.elements) {
      element.stamp(this);
    }
    
    // Solve
    this.matrixSolver.luSolve(this.circuitMatrix, this.circuitRightSide, this.solution);
    
    // Update voltages
    for (const element of this.elements) {
      for (let i = 0; i < element.nodes.length; i++) {
        element.volts[i] = this.solution[element.nodes[i]] || 0;
      }
      element.current = (element.volts[0] - element.volts[1]) / 1000; // Approximate
    }
    
    this.currentTime += this.timeStep;
  }

  private analyze(): void {
    this.nodeMap.clear();
    this.nodeCount = 0;
    this.nodeMap.set('0,0', 0);

    for (const element of this.elements) {
      element.allocNodes();
      for (let i = 0; i < element.getPostCount(); i++) {
        const post = element.getPost(i);
        const key = this.getNodeKey(post);
        if (!this.nodeMap.has(key)) {
          this.nodeMap.set(key, ++this.nodeCount);
        }
        element.nodes[i] = this.nodeMap.get(key)!;
      }
    }

    this.matrixSize = this.nodeCount + 1;
    this.circuitMatrix = Array(this.matrixSize).fill(null)
      .map(() => Array(this.matrixSize).fill(0));
    this.circuitRightSide = Array(this.matrixSize).fill(0);
    this.solution = Array(this.matrixSize).fill(0);

    // Stamp all elements
    for (const element of this.elements) {
      element.stamp(this);
    }

    this.matrixSolver.luFactor(this.circuitMatrix);
  }

  stampResistor(n1: number, n2: number, g: number): void {
    if (n1 !== 0) {
      this.circuitMatrix[n1][n1] += g;
      if (n2 !== 0) this.circuitMatrix[n1][n2] -= g;
    }
    if (n2 !== 0) {
      this.circuitMatrix[n2][n2] += g;
      if (n1 !== 0) this.circuitMatrix[n2][n1] -= g;
    }
  }

  private getNodeKey(point: Point): string {
    const gridSize = 20;
    const x = Math.round(point.x / gridSize) * gridSize;
    const y = Math.round(point.y / gridSize) * gridSize;
    return `${x},${y}`;
  }

  reset(): void {
    this.currentTime = 0;
    for (const element of this.elements) {
      element.current = 0;
      element.volts.fill(0);
    }
  }

  clearCircuit(): void {
    this.elements = [];
    this.currentTime = 0;
  }
}
```

---

## Adding Components

### Step 7: Create Resistor (5 minutes)

Create `src/simulator/elements/passive/Resistor.ts`:

```typescript
import { CircuitElement } from '../base/CircuitElement';
import { Rectangle } from '../../../utils/Rectangle';
import { Point } from '../../../utils/Point';

export class Resistor extends CircuitElement {
  resistance: number;

  constructor(x: number, y: number, x2: number, y2: number, resistance: number = 1000) {
    super(x, y, x2, y2);
    this.resistance = resistance;
    this.boundingBox = Rectangle.fromPoints(new Point(x, y), new Point(x2, y2), 10);
  }

  stamp(sim: any): void {
    const g = 1.0 / this.resistance;
    sim.stampResistor(this.nodes[0], this.nodes[1], g);
    this.current = (this.volts[0] - this.volts[1]) / this.resistance;
  }

  draw(ctx: CanvasRenderingContext2D): void {
    ctx.strokeStyle = this.selected ? '#00ffff' : '#ffffff';
    ctx.lineWidth = 2;

    // Draw zigzag
    ctx.beginPath();
    ctx.moveTo(this.x, this.y);
    
    const segments = 6;
    const dx = (this.x2 - this.x) / segments;
    const dy = (this.y2 - this.y) / segments;
    const perpX = -dy;
    const perpY = dx;
    const zigzagWidth = 8;

    for (let i = 1; i <= segments; i++) {
      const offset = (i % 2 === 0 ? 1 : -1) * zigzagWidth;
      const px = this.x + dx * i;
      const py = this.y + dy * i;
      const len = Math.sqrt(dx * dx + dy * dy);
      ctx.lineTo(px + perpX * offset / len, py + perpY * offset / len);
    }

    ctx.stroke();

    // Draw posts
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(this.x, this.y, 3, 0, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(this.x2, this.y2, 3, 0, 2 * Math.PI);
    ctx.fill();

    // Draw value
    ctx.fillStyle = '#ffffff';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    const text = this.resistance >= 1000 
      ? `${(this.resistance / 1000).toFixed(1)}kΩ`
      : `${this.resistance.toFixed(0)}Ω`;
    ctx.fillText(text, (this.x + this.x2) / 2, (this.y + this.y2) / 2 - 10);
  }
}
```

### Step 8: Create Voltage Source (5 minutes)

Create `src/simulator/elements/sources/VoltageSource.ts`:

```typescript
import { CircuitElement } from '../base/CircuitElement';
import { Rectangle } from '../../../utils/Rectangle';
import { Point } from '../../../utils/Point';

export class VoltageSource extends CircuitElement {
  voltage: number;

  constructor(x: number, y: number, x2: number, y2: number, voltage: number = 5) {
    super(x, y, x2, y2);
    this.voltage = voltage;
    this.boundingBox = Rectangle.fromPoints(new Point(x, y), new Point(x2, y2), 20);
  }

  stamp(sim: any): void {
    // Simplified: treat as very low resistance with forced voltage
    sim.stampResistor(this.nodes[0], this.nodes[1], 1e6);
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const cx = (this.x + this.x2) / 2;
    const cy = (this.y + this.y2) / 2;
    const radius = 15;

    // Draw circle
    ctx.strokeStyle = this.selected ? '#00ffff' : '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
    ctx.stroke();

    // Draw leads
    ctx.beginPath();
    ctx.moveTo(this.x, this.y);
    ctx.lineTo(cx - radius, cy);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx + radius, cy);
    ctx.lineTo(this.x2, this.y2);
    ctx.stroke();

    // Draw + and -
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('+', cx + 8, cy - 8);
    ctx.fillText('-', cx - 8, cy + 8);

    // Draw posts
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(this.x, this.y, 3, 0, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(this.x2, this.y2, 3, 0, 2 * Math.PI);
    ctx.fill();

    // Draw value
    ctx.font = '12px Arial';
    ctx.fillText(`${this.voltage}V`, cx, cy + radius + 15);
  }
}
```

### Step 9: Create Wire (5 minutes)

Create `src/simulator/elements/passive/Wire.ts`:

```typescript
import { CircuitElement } from '../base/CircuitElement';
import { Rectangle } from '../../../utils/Rectangle';
import { Point } from '../../../utils/Point';

export class Wire extends CircuitElement {
  constructor(x: number, y: number, x2: number, y2: number) {
    super(x, y, x2, y2);
    this.boundingBox = Rectangle.fromPoints(new Point(x, y), new Point(x2, y2), 5);
  }

  stamp(sim: any): void {
    // Wire has essentially zero resistance
    sim.stampResistor(this.nodes[0], this.nodes[1], 1e6);
  }

  draw(ctx: CanvasRenderingContext2D): void {
    ctx.strokeStyle = this.selected ? '#00ffff' : '#808080';
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.moveTo(this.x, this.y);
    ctx.lineTo(this.x2, this.y2);
    ctx.stroke();

    // Draw posts
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(this.x, this.y, 3, 0, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(this.x2, this.y2, 3, 0, 2 * Math.PI);
    ctx.fill();
  }
}
```

---

## User Interface

### Step 10: Create State Store (5 minutes)

Create `src/store/circuitStore.ts`:

```typescript
import { create } from 'zustand';
import { CircuitSimulator } from '../simulator/core/CircuitSimulator';

interface CircuitStore {
  simulator: CircuitSimulator;
  selectedTool: string | null;
  setSelectedTool: (tool: string | null) => void;
}

export const useCircuitStore = create<CircuitStore>((set) => ({
  simulator: new CircuitSimulator(),
  selectedTool: null,
  setSelectedTool: (tool) => set({ selectedTool: tool }),
}));
```

### Step 11: Create Canvas Component (5 minutes)

Create `src/components/Canvas/Canvas.tsx`:

```typescript
import React, { useRef, useEffect, useState } from 'react';
import { CircuitSimulator } from '../../simulator/core/CircuitSimulator';
import { Point } from '../../utils/Point';
import { Resistor } from '../../simulator/elements/passive/Resistor';
import { VoltageSource } from '../../simulator/elements/sources/VoltageSource';
import { Wire } from '../../simulator/elements/passive/Wire';
import { useCircuitStore } from '../../store/circuitStore';

interface CanvasProps {
  width: number;
  height: number;
  isRunning: boolean;
}

export const Canvas: React.FC<CanvasProps> = ({ width, height, isRunning }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const simulator = useCircuitStore(state => state.simulator);
  const selectedTool = useCircuitStore(state => state.selectedTool);
  const [dragStart, setDragStart] = useState<Point | null>(null);
  const [dragEnd, setDragEnd] = useState<Point | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const animate = () => {
      if (isRunning) simulator.simulate();

      // Clear
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, width, height);

      // Draw grid
      ctx.strokeStyle = '#222';
      ctx.lineWidth = 0.5;
      for (let x = 0; x < width; x += 20) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += 20) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Draw elements
      for (const element of simulator.elements) {
        element.draw(ctx);
      }

      // Draw temp element
      if (dragStart && dragEnd) {
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(dragStart.x, dragStart.y);
        ctx.lineTo(dragEnd.x, dragEnd.y);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      requestAnimationFrame(animate);
    };

    animate();
  }, [simulator, width, height, isRunning, dragStart, dragEnd]);

  const snap = (p: Point) => new Point(
    Math.round(p.x / 20) * 20,
    Math.round(p.y / 20) * 20
  );

  const handleMouseDown = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const p = snap(new Point(e.clientX - rect.left, e.clientY - rect.top));
    setDragStart(p);
    setDragEnd(p);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragStart) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const p = snap(new Point(e.clientX - rect.left, e.clientY - rect.top));
    setDragEnd(p);
  };

  const handleMouseUp = () => {
    if (dragStart && dragEnd && selectedTool) {
      let element;
      if (selectedTool === 'resistor') {
        element = new Resistor(dragStart.x, dragStart.y, dragEnd.x, dragEnd.y, 1000);
      } else if (selectedTool === 'voltage') {
        element = new VoltageSource(dragStart.x, dragStart.y, dragEnd.x, dragEnd.y, 5);
      } else if (selectedTool === 'wire') {
        element = new Wire(dragStart.x, dragStart.y, dragEnd.x, dragEnd.y);
      }
      if (element) simulator.addElement(element);
    }
    setDragStart(null);
    setDragEnd(null);
  };

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      style={{ border: '2px solid #444', cursor: selectedTool ? 'crosshair' : 'default' }}
    />
  );
};
```

### Step 12: Create Toolbar (3 minutes)

Create `src/components/Toolbar/Toolbar.tsx`:

```typescript
import React from 'react';
import { useCircuitStore } from '../../store/circuitStore';

export const Toolbar: React.FC = () => {
  const { selectedTool, setSelectedTool } = useCircuitStore();

  const Button = ({ tool, label }: { tool: string; label: string }) => (
    <button
      onClick={() => setSelectedTool(tool)}
      style={{
        padding: '10px 20px',
        background: selectedTool === tool ? '#0066cc' : '#333',
        color: '#fff',
        border: 'none',
        cursor: 'pointer',
        margin: '5px'
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{ background: '#222', padding: '10px' }}>
      <Button tool="wire" label="Wire" />
      <Button tool="resistor" label="Resistor" />
      <Button tool="voltage" label="Voltage" />
    </div>
  );
};
```

### Step 13: Create Main App (2 minutes)

Update `src/App.tsx`:

```typescript
import React, { useState } from 'react';
import { Canvas } from './components/Canvas/Canvas';
import { Toolbar } from './components/Toolbar/Toolbar';
import { useCircuitStore } from './store/circuitStore';

function App() {
  const [isRunning, setIsRunning] = useState(true);
  const simulator = useCircuitStore(state => state.simulator);

  return (
    <div style={{ background: '#111', minHeight: '100vh', color: '#fff' }}>
      <div style={{ padding: '10px', background: '#000', display: 'flex', gap: '10px' }}>
        <button onClick={() => setIsRunning(!isRunning)}>
          {isRunning ? 'Pause' : 'Run'}
        </button>
        <button onClick={() => simulator.reset()}>Reset</button>
        <button onClick={() => simulator.clearCircuit()}>Clear</button>
        <span style={{ marginLeft: 'auto' }}>
          Time: {simulator.currentTime.toFixed(6)}s | 
          Elements: {simulator.elements.length}
        </span>
      </div>
      <Toolbar />
      <div style={{ display: 'flex', justifyContent: 'center', padding: '20px' }}>
        <Canvas width={1000} height={600} isRunning={isRunning} />
      </div>
    </div>
  );
}

export default App;
```

---

## Testing

### Step 14: Test the Simulator

1. Start the dev server: `npm run dev`
2. Click "Voltage" button
3. Drag on canvas to create voltage source (vertical)
4. Click "Resistor" button
5. Drag to create resistor
6. Click "Wire" button
7. Connect voltage source to resistor with wires
8. Connect back to voltage source to complete circuit
9. Watch the simulation run!

### Example Circuits to Try

#### RC Circuit
```
1. Add voltage source (5V)
2. Add resistor (1kΩ)
3. Add capacitor (100µF) - you'll need to implement this
4. Connect in series with wires
5. Watch charging/discharging behavior
```

#### Voltage Divider
```
1. Add voltage source (10V)
2. Add resistor R1 (1kΩ)
3. Add resistor R2 (1kΩ)
4. Connect in series
5. Measure voltage at midpoint (should be 5V)
```

---

## Next Steps

### Enhance the Simulator

1. **Add More Components**:
   - Capacitor
   - Inductor
   - Diode
   - Transistor
   - Logic gates

2. **Improve UI**:
   - Add property editor for components
   - Implement scope/oscilloscope
   - Add zoom/pan
   - Implement save/load

3. **Add Features**:
   - Component values editor
   - Delete components (keyboard shortcut)
   - Undo/redo
   - Circuit validation
   - Error messages

4. **Optimize Performance**:
   - Use Web Workers for simulation
   - Implement dirty regions for rendering
   - Add FPS counter
   - Optimize matrix operations

### Resources

- Full documentation in `SIMULATOR_ARCHITECTURE.md`
- Advanced components in `ADVANCED_COMPONENTS_GUIDE.md`
- Complete implementation in `REACTJS_IMPLEMENTATION_GUIDE.md`

---

## Troubleshooting

### Common Issues

**Circuit doesn't simulate:**
- Make sure circuit is closed (forms complete loop)
- Check that all nodes are connected properly
- Verify voltage source is present

**Elements don't connect:**
- Nodes must be on grid points (snap to 20px grid)
- Make sure endpoints touch exactly

**Performance issues:**
- Reduce timestep
- Simplify circuit
- Limit number of elements

**Matrix is singular:**
- Circuit has disconnected nodes
- Add resistor to ground
- Check for floating nodes

---

## Congratulations!

You now have a working circuit simulator! The basic implementation demonstrates:

✅ Circuit simulation using Modified Nodal Analysis
✅ Interactive canvas with element placement
✅ Real-time simulation
✅ Resistors, voltage sources, and wires
✅ Clean React + TypeScript architecture

Continue learning with the detailed documentation files to add more advanced features!
