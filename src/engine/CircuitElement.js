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