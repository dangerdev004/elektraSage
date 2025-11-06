import CircuitElement from '../CircuitElement';

export default class WireElm extends CircuitElement {
  constructor(x1, y1, x2, y2, params, f) {
    super(x1, y1, x2, y2, params, f);
  }

  getDumpType() { return 'w'; }

  draw(graphics) {
    graphics.lineWidth = 2;
    graphics.strokeStyle = this.selected ? "cyan" : "white";
    graphics.beginPath();
    graphics.moveTo(this.x1, this.y1);
    graphics.lineTo(this.x2, this.y2);
    graphics.stroke();
    
    this.drawPost(graphics, this.x1, this.y1);
    this.drawPost(graphics, this.x2, this.y2);
  }

  stamp(stamper) {
    // A wire is a 0V voltage source between its two nodes
    // Note: This is inefficient. CirSim.java uses node collapsing,
    // but this (stamping a 0V source) is the "easy" way to do it.
    // We'll need to add getVoltageSourceCount() to WireElm.
    
    // Let's use the 1e-6 Ohm resistor method instead, it's simpler
    stamper.stampResistor(this.nodes[0], this.nodes[1], 1e-6);
  }
}