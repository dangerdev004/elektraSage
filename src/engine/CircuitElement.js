export default class CircuitElement {
  constructor(x1, y1, x2, y2, params = {}, f = 0) {
    this.x1 = x1;
    this.y1 = y1;
    this.x2 = x2;
    this.y2 = y2;
    this.flags = f;
    this.params = params;

    this.nodes = new Array(this.getPostCount()).fill(-1);
    this.volts = new Array(this.getPostCount()).fill(0);
    this.current = 0;
    this.curcount = 0;

    this.noDiagonal = false;
    this.selected = false;
  }

  // --- Standard methods expected by CircuitSimulator ---

  /**
   * Returns the number of connection points (posts).
   * Defaults to 2 for most components.
   */
  getPostCount() {
    return 2;
  }

  /**
   * Returns the coordinates of a specific post.
   */
  getPost(n) {
    if (n === 0) return { x: this.x1, y: this.y1 };
    if (n === 1) return { x: this.x2, y: this.y2 };
    return null;
  }

  setNode(p, n) {
    this.nodes[p] = n;
  }

  getNode(p) {
    return this.nodes[p];
  }

  setVoltage(p, v) {
    this.volts[p] = v;
  }

  getVoltage(p) {
    return this.volts[p];
  }

  /**
   * Returns the voltage difference between the first two posts.
   */
  getVoltageDiff() {
    return this.volts[0] - this.volts[1];
  }

  /**
   * Indicates if this element requires non-linear solving (Newton-Raphson).
   * Defaults to false (linear).
   */
  nonLinear() {
    return false;
  }

  /**
   * Returns the number of internal voltage sources this element provides.
   * Defaults to 0.
   */
  getVoltageSourceCount() {
    return 0;
  }

  setVoltageSource(n, v) {
    // Default implementation does nothing
  }

  setCurrent(v, c) {
    this.current = c;
  }

  getCurrent() {
    return this.current;
  }

  reset() {
    this.volts.fill(0);
    this.current = 0;
  }

  distanceToLineSegment(px, py, x1, y1, x2, y2) {
    const l2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
    if (l2 === 0) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)));
  }

  /**
   * Checks if a specific post is close to (x,y)
   * Returns index of post (0 or 1) or -1 if none.
   */
  getPostAt(x, y, threshold = 10) {
      if (Math.hypot(x - this.x1, y - this.y1) < threshold) return 0;
      if (Math.hypot(x - this.x2, y - this.y2) < threshold) return 1;
      return -1;
  }

  updateDotCount(curScale) {
     this.curcount = (this.curcount + this.current * curScale) % 16;
  }

  getMouseDistance(x, y) {
    return this.distanceToLineSegment(x, y, this.x1, this.y1, this.x2, this.y2);
  }
  
  drawDots(graphics) {
    if (Math.abs(this.current) < 1e-9) return;

    const dx = this.x2 - this.x1;
    const dy = this.y2 - this.y1;
    const dn = Math.sqrt(dx * dx + dy * dy);
    
    // 16 is standard spacing between dots in standard CircuitJS
    const ds = 16; 
    
    graphics.fillStyle = "#FF0"; // Yellow dots
    
    // Start loop from the current offset (curcount)
    for (let p = this.curcount; p < dn; p += ds) {
      if (p < 0) continue; // Skip dots before the start post
      
      // Linear interpolation to find dot position on the line
      const x = this.x1 + (p * dx) / dn;
      const y = this.y1 + (p * dy) / dn;
      
      graphics.beginPath();
      // Draw a small 2x2 square for the dot (faster than full circles for many dots)
      graphics.rect(x - 1, y - 1, 3, 3); 
      graphics.fill();
    }
  }

  // --- Drawing & UI ---

  draw(graphics) {
    graphics.lineWidth = 2;
    graphics.strokeStyle = this.selected ? "cyan" : "white";
    graphics.beginPath();
    graphics.moveTo(this.x1, this.y1);
    graphics.lineTo(this.x2, this.y2);
    graphics.stroke();

    for (let i = 0; i < this.getPostCount(); i++) {
      const p = this.getPost(i);
      this.drawPost(graphics, p.x, p.y);
    }
  }

  drawPost(graphics, x, y) {
    graphics.fillStyle = "white";
    graphics.beginPath();
    graphics.arc(x, y, 3, 0, 2 * Math.PI);
    graphics.fill();
  }

  getBoundingBox() {
    const minX = Math.min(this.x1, this.x2);
    const minY = Math.min(this.y1, this.y2);
    const maxX = Math.max(this.x1, this.x2);
    const maxY = Math.max(this.y1, this.y2);
    return {
      x: minX - 5,
      y: minY - 5,
      width: maxX - minX + 10,
      height: maxY - minY + 10,
    };
  }

  //Placeholder for simulation
  stamp(stamper) {}
  doStep(stamper) {}
  calculateCurrent() {}
}