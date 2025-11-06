import CircuitElement from '../CircuitElement';

export default class VoltageElm extends CircuitElement {
  constructor(x1, y1, x2, y2, params, f) {
    super(x1, y1, x2, y2, params, f);
    this.maxVoltage = params.voltage || 5;
    this.voltSource = 0; // The index of this voltage source
  }
  
  getVoltageSourceCount() { return 1; }
  setVoltageSource(n, vs) { this.voltSource = vs; }

  getDumpType() { return 'v'; }

  draw(graphics) {
    // ... (drawing code from previous step is fine)
    super.draw(graphics);
    const midX = (this.x1 + this.x2) / 2;
    const midY = (this.y1 + this.y2) / 2;
    graphics.fillStyle = "white";
    graphics.beginPath();
    graphics.arc(midX, midY, 12, 0, 2 * Math.PI);
    graphics.fill();
    graphics.fillStyle = "black";
    graphics.font = "bold 14px sans-serif";
    graphics.textAlign = "center";
    graphics.textBaseline = "middle";
    graphics.fillText("V", midX, midY);
  }

  stamp(stamper) {
    // Tell the simulator to add this voltage source
    stamper.stampVoltageSource(this.nodes[0], this.nodes[1], this.voltSource, this.getVoltageDiff());
  }
  
  getVoltageDiff() {
      return this.maxVoltage;
  }
}