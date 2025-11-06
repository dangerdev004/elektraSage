/**
 * Represents a connection node in the circuit.
 * All element posts connected by wires will share one CircuitNode.
 */
export default class CircuitNode {
  constructor() {
    // List of element posts attached to this node
    this.links = [];
    this.internal = false; // Internal nodes are not drawn
  }
}

/**
 * A link connecting an element post to a CircuitNode.
 */
export class CircuitNodeLink {
  constructor(elm, postIndex) {
    this.elm = elm; // The CircuitElement
    this.num = postIndex; // The post index on that element (e.g., 0 or 1)
  }
}