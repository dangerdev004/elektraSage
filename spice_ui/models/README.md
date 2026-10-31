# Model library

Drop SPICE model files here (`.lib`, `.mod`, `.model`, `.cir`, `.sp`, `.inc`, `.txt`), then use
Simulation > Model Library... > Refresh in the app.

* `.model NAME TYPE(...)` cards are listed and can be picked in a part's Edit dialog
  (D for diodes/LEDs/zeners, NPN, PNP, NMOS, PMOS).
* `.subckt` definitions are listed too, but cannot be assigned to parts yet.
* Respect each model's licence before sharing it. Files here are included into the simulation by the
  local server only when a part in your circuit uses a model from that file.
* The folder can be moved with the `MODELS_DIR` environment variable.
