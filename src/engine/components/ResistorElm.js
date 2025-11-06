import CircuitElement from '../CircuitElement';

export default class ResistorElm extends CircuitElement {
  constructor(x1, y1, x2, y2, params, f) {
    super(x1, y1, x2, y2, params, f);
    this.resistance = params.resistance || 1000;
  }

  getDumpType() { return 'r'; }

  draw(graphics) {
    // Standard draw
    super.draw(graphics);

    // Draw label
    const midX = (this.x1 + this.x2) / 2;
    const midY = (this.y1 + this.y2) / 2;
    graphics.fillStyle = "white";
    graphics.font = "12px sans-serif";
    graphics.textAlign = "center";
    graphics.fillText(`${this.resistance}Ω`, midX + 10, midY - 10);
    
    // Draw calculated voltage and current
    const v1 = this.volts[0];
    const v2 = this.volts[1];
    graphics.fillStyle = "yellow";
    graphics.fillText(`V: ${(v1-v2).toFixed(2)}V`, midX + 10, midY + 10);
    graphics.fillText(`I: ${(this.current*1000).toFixed(2)}mA`, midX + 10, midY + 25);
  }
  
  calculateCurrent() {
     this.current = (this.volts[0] - this.volts[1]) / this.resistance;
  }

  stamp(stamper) {
    // Add our conductance (1/R) to the matrix
    stamper.stampResistor(this.nodes[0], this.nodes[1], this.resistance);
  }
}