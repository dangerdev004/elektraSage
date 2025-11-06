import CircuitNode, { CircuitNodeLink } from './CircuitNode';
import GroundElm from './components/GroundElm';

// Ported from RowInfo.java
class RowInfo {
  static ROW_NORMAL = 0;
  static ROW_CONST = 1;
  constructor() {
    this.type = RowInfo.ROW_NORMAL;
    this.value = 0;
    this.mapCol = 0;
    this.mapRow = 0;
    this.rsChanges = false;
    this.lsChanges = false;
    this.dropRow = false;
  }
}

export default class CircuitSimulator {
  constructor() {
    this.time = 0;
    this.timeStep = 5e-6; // Default timestep
    this.converged = false;
    
    this.nodeList = [];
    this.elmList = [];
    this.voltageSources = [];
    
    this.circuitMatrix = [];
    this.circuitRightSide = [];
    this.origMatrix = [];
    this.origRightSide = [];
    this.circuitRowInfo = [];
    this.circuitPermute = [];
    
    this.circuitMatrixSize = 0;
    this.circuitMatrixFullSize = 0;
    this.circuitNeedsMap = false;
    this.circuitNonLinear = false;
  }
  
  /**
   * Set the elements for the simulator to use.
   * This triggers a full analysis and stamping.
   * @param {Array<CircuitElement>} elements
   */
  setElements(elements) {
    this.elmList = elements;
    this.analyzeCircuit();
  }

  /**
   * Port of analyzeCircuit()
   * Builds the node list and prepares for stamping.
   */
  analyzeCircuit() {
    if (this.elmList.length === 0) {
      this.nodeList = [];
      this.voltageSources = [];
      return;
    }
    
    this.nodeList = [];
    this.voltageSources = [];
    let vscount = 0;
    this.circuitNonLinear = false;

    // --- 1. Node Allocation (Simplified port of calculateWireClosure + makeNodeList) ---
    const nodeMap = new Map(); // Map<String, number> (key: "x,y", value: nodeIndex)
    let nextNode = 0;

    // Ground node is always 0
    this.nodeList.push(new CircuitNode());
    
    // Pass 1: Allocate nodes for all element posts
    for (const ce of this.elmList) {
      for (let i = 0; i < ce.getPostCount(); i++) {
        const pt = ce.getPost(i);
        const key = `${pt.x},${pt.y}`;
        
        if (ce instanceof GroundElm) {
          nodeMap.set(key, 0); // Connect to ground
          continue;
        }
        
        if (!nodeMap.has(key)) {
          // This is a new node
          nodeMap.set(key, ++nextNode);
          this.nodeList.push(new CircuitNode());
        }
      }
    }
    
    // Pass 2: Connect elements to their node indices and count voltage sources
    for (const ce of this.elmList) {
      if (ce.nonLinear?.()) {
        this.circuitNonLinear = true;
      }
      
      // Assign node indices to element posts
      for (let i = 0; i < ce.getPostCount(); i++) {
        const pt = ce.getPost(i);
        const key = `${pt.x},${pt.y}`;
        const nodeIndex = nodeMap.get(key);
        
        ce.setNode(i, nodeIndex);
        
        // Add to node's link list
        this.nodeList[nodeIndex].links.push(new CircuitNodeLink(ce, i));
      }
      
      // Count voltage sources (like VoltageElm, GroundElm)
      const ivs = ce.getVoltageSourceCount?.() || 0;
      for (let j = 0; j < ivs; j++) {
        this.voltageSources.push(ce);
        ce.setVoltageSource(j, vscount++);
      }
    }
    
    this.voltageSourceCount = vscount;
    this.stampCircuit();
  }

  /**
   * Port of stampCircuit()
   * Allocates and fills the matrix based on element properties.
   */
  stampCircuit() {
    const matrixSize = this.nodeList.length - 1 + this.voltageSourceCount;
    if (matrixSize === 0) return;

    this.circuitMatrix = Array.from({ length: matrixSize }, () => new Array(matrixSize).fill(0));
    this.circuitRightSide = new Array(matrixSize).fill(0);
    this.origMatrix = Array.from({ length: matrixSize }, () => new Array(matrixSize).fill(0));
    this.origRightSide = new Array(matrixSize).fill(0);
    
    this.circuitMatrixSize = this.circuitMatrixFullSize = matrixSize;
    this.circuitRowInfo = Array.from({ length: matrixSize }, () => new RowInfo());
    this.circuitPermute = new Array(matrixSize).fill(0);
    this.circuitNeedsMap = false;

    // Stamp all elements
    for (const ce of this.elmList) {
      ce.stamp(this);
    }
    
    // --- We will skip simplifyMatrix() for now, it's a complex optimization ---
    
    // Copy to "orig" arrays
    for(let i = 0; i < matrixSize; i++) {
      this.origRightSide[i] = this.circuitRightSide[i];
      for (let j = 0; j < matrixSize; j++) {
        this.origMatrix[i][j] = this.circuitMatrix[i][j];
      }
    }

    // If circuit is linear, we can factor the matrix just once
    if (!this.circuitNonLinear) {
      if (!this.lu_factor(this.circuitMatrix, this.circuitMatrixSize, this.circuitPermute)) {
        console.error("Singular matrix! Circuit may be invalid.");
      }
    }
  }
  
  /**
   * Port of runCircuit()
   * Solves the matrix for one time step.
   */
  doTimeStep() {
    if (this.elmList.length === 0 || this.circuitMatrixSize === 0) return;

    // Reset matrix/right side from original
    for (let i = 0; i < this.circuitMatrixSize; i++) {
      this.circuitRightSide[i] = this.origRightSide[i];
      if (this.circuitNonLinear) {
        for (let j = 0; j < this.circuitMatrixSize; j++) {
          this.circuitMatrix[i][j] = this.origMatrix[i][j];
        }
      }
    }

    // Call doStep for all elements (e.g., for non-linear components)
    // for (const ce of this.elmList) {
    //   ce.doStep(this);
    // }

    // --- Solve Matrix ---
    if (this.circuitNonLinear) {
      // Re-factor if non-linear
      if (!this.lu_factor(this.circuitMatrix, this.circuitMatrixSize, this.circuitPermute)) {
         console.error("Singular matrix during step!");
         return;
      }
    }
    
    this.lu_solve(this.circuitMatrix, this.circuitMatrixSize, this.circuitPermute, this.circuitRightSide);
    
    // Apply results back to nodes
    this.applySolvedRightSide(this.circuitRightSide);
    
    this.time += this.timeStep;
  }
  
  /**
   * Port of applySolvedRightSide()
   * After solving, this updates all element.volts properties.
   */
  applySolvedRightSide(rs) {
    for (let j = 0; j < this.circuitMatrixFullSize; j++) {
      // (Skipping matrix simplification mapping for now)
      const res = rs[j];

      if (j < this.nodeList.length - 1) {
        // This is a node voltage (index 0 is ground, so j+1)
        const node = this.nodeList[j + 1];
        for (const link of node.links) {
          link.elm.setVoltage(link.num, res);
        }
      } else {
        // This is a voltage source current
        const ji = j - (this.nodeList.length - 1);
        this.voltageSources[ji].setCurrent(ji, res);
      }
    }
    
    // Update element currents (e.g., for resistors)
    for (const ce of this.elmList) {
        ce.calculateCurrent?.();
    }
  }

  // --- Matrix Stamper Methods (from CirSim.java) ---
  
  stampResistor(n1, n2, r) {
    const r0 = 1 / r;
    this.stampMatrix(n1, n1, r0);
    this.stampMatrix(n2, n2, r0);
    this.stampMatrix(n1, n2, -r0);
    this.stampMatrix(n2, n1, -r0);
  }
  
  stampVoltageSource(n1, n2, vsIndex, v) {
    const vn = this.nodeList.length - 1 + vsIndex;
    this.stampMatrix(vn, n1, -1);
    this.stampMatrix(vn, n2, 1);
    this.stampRightSide(vn, v);
    this.stampMatrix(n1, vn, 1);
    this.stampMatrix(n2, vn, -1);
  }
  
  // Stamps a value into the matrix.
  // n1 and n2 are 1-based node indices (0 is ground)
  stampMatrix(n1, n2, val) {
    if (n1 > 0 && n2 > 0) {
      this.circuitMatrix[n1 - 1][n2 - 1] += val;
    }
  }

  // Stamps a value into the right-side vector
  stampRightSide(n, val) {
    if (n > 0) {
      this.circuitRightSide[n - 1] += val;
    }
  }

  // --- Matrix Solver (Ported directly from CirSim.java) ---
  
  lu_factor(a, n, ipvt) {
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < j; i++) {
        let q = a[i][j];
        for (let k = 0; k < i; k++) {
          q -= a[i][k] * a[k][j];
        }
        a[i][j] = q;
      }

      let largest = 0;
      let largestRow = -1;
      for (let i = j; i < n; i++) {
        let q = a[i][j];
        for (let k = 0; k < j; k++) {
          q -= a[i][k] * a[k][j];
        }
        a[i][j] = q;
        const x = Math.abs(q);
        if (x >= largest) {
          largest = x;
          largestRow = i;
        }
      }

      if (j !== largestRow) {
        for (let k = 0; k < n; k++) {
          const x = a[largestRow][k];
          a[largestRow][k] = a[j][k];
          a[j][k] = x;
        }
      }
      ipvt[j] = largestRow;

      if (a[j][j] === 0.0) {
        return false;
      }

      if (j !== n - 1) {
        const mult = 1.0 / a[j][j];
        for (let i = j + 1; i < n; i++) {
          a[i][j] *= mult;
        }
      }
    }
    return true;
  }

  lu_solve(a, n, ipvt, b) {
    let i = 0;
    for (i = 0; i < n; i++) {
      const row = ipvt[i];
      const swap = b[row];
      b[row] = b[i];
      b[i] = swap;
      if (swap !== 0) break;
    }

    let bi = i++;
    for (; i < n; i++) {
      const row = ipvt[i];
      let tot = b[row];
      b[row] = b[i];
      for (let j = bi; j < i; j++) {
        tot -= a[i][j] * b[j];
      }
      b[i] = tot;
    }
    for (i = n - 1; i >= 0; i--) {
      let tot = b[i];
      for (let j = i + 1; j < n; j++) {
        tot -= a[i][j] * b[j];
      }
      b[i] = tot / a[i][i];
    }
  }
}