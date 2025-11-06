import CircuitElement from '../CircuitElement';

export default class GroundElm extends CircuitElement {
  constructor(x1, y1, x2, y2, params, f) {
    super(x1, y1, x2, y2, params, f);
    this.voltSource = 0;
  }

  getPostCount() { return 1; }
  getDumpType() { return 'g'; }
  
  getVoltageSourceCount() { return 1; }
  setVoltageSource(n, vs) { this.voltSource = vs; }

  draw(graphics) {
    // ... (drawing code from previous step is fine)
    super.draw(graphics);
    for (let i = 0; i < 3; i++) {
        const width = 10 - i * 3;
        const yOff = i * 4;
        graphics.beginPath();
        graphics.moveTo(this.x2 - width, this.y2 + yOff);
        graphics.lineTo(this.x2 + width, this.y2 + yOff);
        graphics.stroke();
    }
  }

  stamp(stamper) {
    // A ground is a 0V voltage source from its node (nodes[0]) to the global ground (node 0)
    stamper.stampVoltageSource(this.nodes[0], 0, this.voltSource, 0);
  }
}