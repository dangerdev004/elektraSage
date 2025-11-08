CIRCUIT_METADATA = {
    '3-cgand': {
        'name': '3-Input AND Gate',
        'description': 'Three input AND logic gate',
        'category': 'digital-logic-gates',
        'keywords': ['AND gate', '3-input', 'logic gate', 'digital']
    },
    '3-cgor': {
        'name': '3-Input OR Gate',
        'description': 'Three input OR logic gate',
        'category': 'digital-logic-gates',
        'keywords': ['OR gate', '3-input', 'logic gate', 'digital']
    },
    '3-invert': {
        'name': 'Triple Inverter',
        'description': 'Three NOT gates (inverters)',
        'category': 'digital-logic-gates',
        'keywords': ['NOT gate', 'inverter', 'logic gate', 'digital']
    },
    '3-f211': {
        'name': '3-f211',
        'description': 'Circuit file: 3-f211 (refer to source circuit for details)',
        'category': 'unspecified',
        'keywords': ['3-f211', 'circuit-file']
    },
    '3-f220': {
        'name': '3-f220',
        'description': 'Circuit file: 3-f220 (refer to source circuit for details)',
        'category': 'unspecified',
        'keywords': ['3-f220', 'circuit-file']
    },
    '3-f221': {
        'name': '3-f221',
        'description': 'Circuit file: 3-f221 (refer to source circuit for details)',
        'category': 'unspecified',
        'keywords': ['3-f221', 'circuit-file']
    },
    '3way': {
        'name': '3-Way Switch',
        'description': 'Three-way switching circuit',
        'category': 'switching-circuits',
        'keywords': ['3-way switch', 'switching', 'wiring']
    },
    '4way': {
        'name': '4-Way Switch',
        'description': 'Four-way switching circuit',
        'category': 'switching-circuits',
        'keywords': ['4-way switch', 'switching', 'wiring']
    },
    '555int': {
        'name': '555 Integrator',
        'description': '555-based integrating configuration',
        'category': 'timers-555',
        'keywords': ['555 timer', 'integrator', 'analog']
    },
    '555lowduty': {
        'name': '555 Low Duty Cycle',
        'description': '555 astable with low duty-cycle configuration',
        'category': 'timers-555',
        'keywords': ['555 timer', 'astable', 'low duty cycle', 'PWM']
    },
    '555missing': {
        'name': '555 Missing Pulse Detector',
        'description': 'Detects missing pulses using a 555',
        'category': 'timers-555',
        'keywords': ['555 timer', 'missing pulse', 'detector', 'monostable']
    },
    '555monostable': {
        'name': '555 Monostable',
        'description': 'One-shot pulse generator using 555',
        'category': 'timers-555',
        'keywords': ['555 timer', 'monostable', 'one-shot', 'pulse']
    },
    '555pulsemod': {
        'name': '555 Pulse Modulation',
        'description': 'Pulse-width modulation using 555',
        'category': 'timers-555',
        'keywords': ['555 timer', 'PWM', 'modulation', 'astable']
    },
    '555saw': {
        'name': '555 Sawtooth Generator',
        'description': 'Generates a sawtooth waveform using 555',
        'category': 'timers-555',
        'keywords': ['555 timer', 'sawtooth', 'waveform']
    },
    '555schmitt': {
        'name': '555 Schmitt Trigger',
        'description': '555 used as a Schmitt trigger',
        'category': 'timers-555',
        'keywords': ['555 timer', 'Schmitt trigger', 'hysteresis']
    },
    '555sequencer': {
        'name': '555 Sequencer',
        'description': 'Step sequencer built around 555 timing',
        'category': 'timers-555',
        'keywords': ['555 timer', 'sequencer', 'timing']
    },
    '555square': {
        'name': '555 Square Wave Generator',
        'description': 'Square wave oscillator using 555',
        'category': 'timers-555',
        'keywords': ['555 timer', 'square wave', 'oscillator', 'astable']
    },
    '7segdecoder': {
        'name': '7-Segment Decoder',
        'description': 'Binary/BCD to 7-segment decoder logic',
        'category': 'digital-logic-decoders',
        'keywords': ['7-segment', 'decoder', 'display', 'digital']
    },
    'allpass1': {
        'name': 'All-Pass Filter (1st Order)',
        'description': 'First-order all-pass filter',
        'category': 'analog-filters',
        'keywords': ['all-pass', 'filter', 'phase', 'first order']
    },
    'allpass2': {
        'name': 'All-Pass Filter (2nd Order)',
        'description': 'Second-order all-pass filter',
        'category': 'analog-filters',
        'keywords': ['all-pass', 'filter', 'phase', 'second order']
    },
    'amdetect': {
        'name': 'AM Detector',
        'description': 'Amplitude modulation detector',
        'category': 'analog-demodulation',
        'keywords': ['AM', 'detector', 'demodulation', 'envelope']
    },
    'amp-dfdx': {
        'name': 'Op-Amp Differentiator (d/dt)',
        'description': 'Operational amplifier differentiator',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'differentiator', 'analog']
    },
    'amp-diff': {
        'name': 'Differential Amplifier',
        'description': 'Op-amp differential amplifier',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'differential amplifier', 'instrumentation']
    },
    'amp-follower': {
        'name': 'Voltage Follower (Buffer)',
        'description': 'Op-amp buffer (unity gain)',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'voltage follower', 'buffer', 'unity gain']
    },
    'amp-fullrect': {
        'name': 'Precision Full-Wave Rectifier',
        'description': 'Op-amp precision full-wave rectifier',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'rectifier', 'full-wave', 'precision']
    },
    'amp-integ': {
        'name': 'Op-Amp Integrator',
        'description': 'Operational amplifier integrator',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'integrator', 'analog']
    },
    'amp-invert': {
        'name': 'Inverting Amplifier',
        'description': 'Op-amp inverting configuration',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'inverting amplifier', 'gain']
    },
    'amp-noninvert': {
        'name': 'Non-Inverting Amplifier',
        'description': 'Op-amp non-inverting configuration',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'non-inverting amplifier', 'gain']
    },
    'amp-rect': {
        'name': 'Precision Half-Wave Rectifier',
        'description': 'Op-amp precision half-wave rectifier',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'rectifier', 'half-wave', 'precision']
    },
    'amp-schmitt': {
        'name': 'Op-Amp Schmitt Trigger',
        'description': 'Op-amp based Schmitt trigger',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'Schmitt trigger', 'hysteresis']
    },
    'amp-sum': {
        'name': 'Summing Amplifier',
        'description': 'Op-amp summing amplifier circuit',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'summing amplifier', 'adder', 'analog']
    },
    'bandpass': {
        'name': 'Band-Pass Filter',
        'description': 'Standard band-pass filter circuit',
        'category': 'analog-filters',
        'keywords': ['band-pass', 'filter', 'analog', 'frequency response']
    },
    'besselbutter': {
        'name': 'Bessel vs Butterworth Filter Comparison',
        'description': 'Compares Bessel and Butterworth filter responses',
        'category': 'analog-filters',
        'keywords': ['Bessel filter', 'Butterworth filter', 'comparison', 'analog']
    },
    'blank': {
        'name': 'Blank Circuit Template',
        'description': 'Empty circuit placeholder with no components',
        'category': 'utility',
        'keywords': ['blank', 'template', 'empty circuit']
    },
    'butter10lo': {
        'name': '10th-Order Butterworth Low-Pass Filter',
        'description': 'Butterworth low-pass filter of order 10',
        'category': 'analog-filters',
        'keywords': ['Butterworth filter', 'low-pass', 'analog', '10th order']
    },
    'cap': {
        'name': 'Capacitor Example',
        'description': 'Basic capacitor demonstration circuit',
        'category': 'passive-components',
        'keywords': ['capacitor', 'RC', 'basic', 'passive']
    },
    'capac': {
        'name': 'Capacitor Charge/Discharge',
        'description': 'RC circuit showing capacitor charging and discharging behavior',
        'category': 'passive-components',
        'keywords': ['capacitor', 'RC circuit', 'charging', 'discharging']
    },
    'capmult': {
        "name": "Op-Amp Based Capacitance Multiplier",
        "description": "Capacitance multiplier circuit using an op-amp to simulate a large capacitor value.",
        "category": "analog-active",
        "keywords": [
            "op-amp",
            "capacitance multiplier",
            "analog",
            "active filter"
        ]
    },
    'capmultcaps': {
        "name": "Capacitance Variation Comparison",
        "description": "Three RC circuits showing voltage response for different capacitance values.",
        "category": "analog-passive",
        "keywords": [
            "RC circuit",
            "capacitor comparison",
            "analog",
            "passive"
        ]
    },
    'capmultfreq': {
        "name": "RC Network Frequency Response",
        "description": "Three RC networks demonstrating amplitude variation with input frequency.",
        "category": "analog-filters",
        "keywords": [
            "RC network",
            "frequency response",
            "analog",
            "filter"
        ]
    },
    'cappar': {
        'name': 'Capacitors in Parallel',
        'description': 'Demonstrates equivalent capacitance for parallel capacitors',
        'category': 'passive-components',
        'keywords': ['capacitor', 'parallel', 'equivalent capacitance']
    },
    'capseries': {
        'name': 'Capacitors in Series',
        'description': 'Demonstrates equivalent capacitance for series capacitors',
        'category': 'passive-components',
        'keywords': ['capacitor', 'series', 'equivalent capacitance']
    },
    'cc2': {
        "name": "Common Collector Amplifier (Behavioral Model)",
        "description": "Behavioral simulation of a common collector amplifier using controlled sources and resistive models.",
        "category": "analog-active",
        "keywords": [
            "emitter follower",
            "behavioral model",
            "analog",
            "BJT equivalent"
        ]
    },
    'cc2imp': {
        "name": "Input Impedance Demonstration (Controlled Source Model)",
        "description": "Demonstrates input-output impedance relations using controlled sources instead of transistors.",
        "category": "analog-active",
        "keywords": [
            "input impedance",
            "controlled source",
            "analog",
            "simulation"
        ]
    },
    'cc2impn': {
        "name": "Input Impedance Model (NPN Equivalent Simulation)",
        "description": "Simulated input impedance of an NPN-based amplifier using controlled-source modeling.",
        "category": "analog-active",
        "keywords": [
            "NPN model",
            "input impedance",
            "analog",
            "simulation"
        ]
    },
    'cc2n': {
        "name": "Common Collector Amplifier Model (NPN Equivalent)",
        "description": "Behavioral model of a common collector amplifier using controlled sources to emulate NPN transistor behavior.",
        "category": "analog-active",
        "keywords": [
            "emitter follower",
            "NPN model",
            "analog",
            "behavioral amplifier"
        ]
    },
    'ccdiff': {
        'name': 'Differential Pair (BJT)',
        'description': 'BJT differential amplifier configuration',
        'category': 'bjt-amplifiers',
        'keywords': ['differential pair', 'BJT', 'amplifier']
    },
    'cciamp': {
        'name': 'Current-Controlled Amplifier',
        'description': 'Amplifier with current-controlled gain',
        'category': 'analog-active',
        'keywords': ['current-controlled amplifier', 'analog', 'gain control']
    },
    'ccinductor': {
        'name': 'Current-Controlled Inductor',
        'description': 'Simulated inductor using current control',
        'category': 'analog-active',
        'keywords': ['current-controlled', 'inductor', 'analog']
    },
    'ccint': {
        'name': 'Current-Controlled Integrator',
        'description': 'Integrator circuit using current control',
        'category': 'analog-active',
        'keywords': ['current-controlled', 'integrator', 'analog']
    },
    'ccitov': {
        'name': 'Current-to-Voltage Converter',
        'description': 'Converts input current to proportional voltage',
        'category': 'signal-converters',
        'keywords': ['current to voltage', 'converter', 'analog']
    },
    'ccvccs': {
        'name': 'Voltage-Controlled Current Source (VCCS)',
        'description': 'Generates current proportional to control voltage',
        'category': 'analog-active',
        'keywords': ['VCCS', 'voltage controlled', 'current source']
    },
    'ceamp': {
        'name': 'Common Emitter Amplifier',
        'description': 'BJT common emitter amplifier configuration',
        'category': 'bjt-amplifiers',
        'keywords': ['common emitter', 'BJT', 'amplifier', 'gain']
    },
    'classd': {
        'name': 'Class-D Amplifier',
        'description': 'Switching power amplifier (Class D) demonstration',
        'category': 'power-amplifiers',
        'keywords': ['Class D', 'amplifier', 'PWM', 'switching']
    },
    'clockedsrff': {
        'name': 'Clocked SR Flip-Flop',
        'description': 'S-R flip-flop with clock control input',
        'category': 'digital-sequential',
        'keywords': ['SR flip-flop', 'clocked', 'sequential', 'digital']
    },
    'cmosff': {
        'name': 'CMOS Flip-Flop',
        'description': 'Flip-flop built using CMOS logic gates',
        'category': 'digital-cmos',
        'keywords': ['CMOS', 'flip-flop', 'digital']
    },
    'cmosinverter': {
        'name': 'CMOS Inverter',
        'description': 'Basic CMOS inverter (NOT gate)',
        'category': 'digital-cmos',
        'keywords': ['CMOS', 'inverter', 'NOT gate', 'digital']
    },
    'cmosinvertercap': {
        'name': 'CMOS Inverter with Capacitive Load',
        'description': 'CMOS inverter loaded with a capacitor to show delay',
        'category': 'digital-cmos',
        'keywords': ['CMOS inverter', 'capacitive load', 'delay', 'digital']
    },
    'cmosinverterslow': {
        'name': 'CMOS Inverter (Slow Response)',
        'description': 'CMOS inverter circuit showing slow switching response',
        'category': 'digital-cmos',
        'keywords': ['CMOS inverter', 'slow switching', 'digital']
    },
    'cmosmsff': {
        'name': 'CMOS Master-Slave Flip-Flop',
        'description': 'Master-slave D flip-flop built using CMOS logic',
        'category': 'digital-cmos',
        'keywords': ['CMOS', 'master-slave flip-flop', 'D flip-flop', 'digital']
    },
    'cmosnand': {
        'name': 'CMOS NAND Gate',
        'description': 'CMOS logic NAND gate circuit',
        'category': 'digital-cmos',
        'keywords': ['CMOS', 'NAND gate', 'digital logic']
    },
    'cmosnor': {
        'name': 'CMOS NOR Gate',
        'description': 'CMOS logic NOR gate circuit',
        'category': 'digital-cmos',
        'keywords': ['CMOS', 'NOR gate', 'digital logic']
    },
    'cmostransgate': {
        'name': 'CMOS Transmission Gate',
        'description': 'Bidirectional analog switch using CMOS transmission gate',
        'category': 'digital-cmos',
        'keywords': ['CMOS', 'transmission gate', 'analog switch']
    },
    'cmosxor': {
        'name': 'CMOS XOR Gate',
        'description': 'CMOS logic XOR gate circuit',
        'category': 'digital-cmos',
        'keywords': ['CMOS', 'XOR gate', 'digital logic']
    },
    'colpitts': {
        'name': 'Colpitts Oscillator',
        'description': 'LC oscillator using Colpitts configuration',
        'category': 'oscillators',
        'keywords': ['Colpitts oscillator', 'LC', 'analog', 'frequency']
    },
    'counter': {
        'name': '4-Bit Binary Counter',
        'description': '4-bit synchronous binary counter circuit',
        'category': 'digital-sequential',
        'keywords': ['binary counter', '4-bit', 'sequential', 'digital']
    },
    'counter8': {
        'name': '8-Bit Binary Counter',
        'description': '8-bit synchronous binary counter circuit',
        'category': 'digital-sequential',
        'keywords': ['binary counter', '8-bit', 'sequential', 'digital']
    },
    'coupled1': {
        'name': 'Coupled Inductors (Single Pair)',
        'description': 'Basic two-coil coupled inductor demonstration',
        'category': 'magnetics',
        'keywords': ['coupled inductors', 'mutual inductance', 'transformer']
    },
    'coupled2': {
        'name': 'Coupled Inductors (Dual Pair)',
        'description': 'Demonstrates dual-pair magnetic coupling',
        'category': 'magnetics',
        'keywords': ['coupled inductors', 'mutual coupling', 'magnetics']
    },
    'coupled3': {
        'name': 'Coupled Inductors (Triple)',
        'description': 'Three inductors demonstrating magnetic coupling effects',
        'category': 'magnetics',
        'keywords': ['coupled inductors', 'triple', 'mutual inductance', 'magnetic coupling']
    },
    'crossover': {
        'name': 'Audio Crossover Network',
        'description': 'High-pass and low-pass crossover filter for audio applications',
        'category': 'analog-filters',
        'keywords': ['crossover', 'audio', 'filter', 'high-pass', 'low-pass']
    },
    'cube': {
        'name': 'Nonlinear Cubing Circuit',
        'description': 'Analog cubing circuit producing output proportional to input³',
        'category': 'analog-math',
        'keywords': ['analog computing', 'cube', 'nonlinear', 'math circuit']
    },
    'currentsrc': {
        'name': 'Constant Current Source',
        'description': 'Basic constant current source using transistors or op-amps',
        'category': 'analog-sources',
        'keywords': ['current source', 'constant current', 'analog']
    },
    'currentsrcelm': {
        'name': 'Current Source Element',
        'description': 'Simplified current source element for modular use',
        'category': 'analog-sources',
        'keywords': ['current source', 'element', 'analog', 'modular']
    },
    'currentsrcramp': {
        'name': 'Current Source Ramp Generator',
        'description': 'Generates a ramp waveform using a current source',
        'category': 'signal-generators',
        'keywords': ['current source', 'ramp generator', 'waveform', 'analog']
    },
    'dac': {
        'name': 'Digital-to-Analog Converter (R-2R DAC)',
        'description': 'Basic R-2R ladder DAC converting digital input to analog output',
        'category': 'data-conversion',
        'keywords': ['DAC', 'R-2R', 'digital to analog', 'converter']
    },
    'darlington': {
        'name': 'Darlington Pair',
        'description': 'Two-transistor Darlington pair for high current gain',
        'category': 'bjt-configurations',
        'keywords': ['Darlington pair', 'BJT', 'gain', 'transistor']
    },
    'dcrestoration': {
        'name': 'DC Restoration Circuit',
        'description': 'Restores DC level to AC coupled signals (clamper circuit)',
        'category': 'analog-signal-conditioning',
        'keywords': ['DC restoration', 'clamper', 'signal conditioning']
    },
    'deccounter': {
        'name': 'Decade Counter',
        'description': 'Decimal (0–9) counter circuit',
        'category': 'digital-sequential',
        'keywords': ['decade counter', 'BCD', 'sequential', 'digital']
    },
    'decoder': {
        'name': 'Binary Decoder',
        'description': 'Converts binary input into one-hot output',
        'category': 'digital-combinational',
        'keywords': ['decoder', 'binary', 'logic', 'digital']
    },
    'delayrc': {
        "name": "Two-Stage RC Delay Demonstration",
        "description": "Shows delay and phase shift through cascaded RC networks using test sources and markers",
        "category": "analog-filters",
        "keywords": ["RC network", "delay", "phase shift", "analog", "cascaded"]
    },
    'deltasigma': {
        'name': 'Delta-Sigma Modulator',
        'description': 'Analog-to-digital modulator using delta-sigma technique',
        'category': 'data-conversion',
        'keywords': ['delta-sigma', 'modulator', 'ADC', 'oversampling']
    },
    'diff': {
        "name": "RC Differentiator Circuit",
        "description": "Simple passive differentiator circuit using resistor and capacitor",
        "category": "analog-filters",
        "keywords": ["RC", "differentiator", "passive", "analog"]
    },
    'digcompare': {
        'name': 'Digital Comparator',
        'description': 'Compares two digital inputs and outputs logic high/low',
        'category': 'digital-combinational',
        'keywords': ['comparator', 'digital', 'logic', 'comparison']
    },
    'digsine': {
        'name': 'Digital Sine Wave Generator',
        'description': 'Generates a digital approximation of a sine waveform',
        'category': 'signal-generators',
        'keywords': ['digital sine', 'waveform', 'generator', 'lookup table']
    },
    'diodeclip': {
        'name': 'Diode Clipping Circuit',
        'description': 'Clips voltage waveform using diodes',
        'category': 'analog-signal-conditioning',
        'keywords': ['diode clipper', 'limiter', 'wave shaping']
    },
    'diodecurve': {
        'name': 'Diode IV Characteristic',
        'description': 'Plots current-voltage behavior of a diode',
        'category': 'semiconductor-devices',
        'keywords': ['diode', 'IV curve', 'semiconductor', 'characteristic']
    },
    'diodelimit': {
        'name': 'Diode Limiter',
        'description': 'Voltage limiting circuit using diodes',
        'category': 'analog-signal-conditioning',
        'keywords': ['diode limiter', 'voltage limit', 'analog']
    },
    'diodevar': {
        'name': 'Varactor Diode',
        'description': 'Demonstrates voltage-dependent capacitance of varactor diode',
        'category': 'semiconductor-devices',
        'keywords': ['varactor', 'diode', 'capacitance', 'tuning']
    },
    'divideby2': {
        'name': 'Divide-by-2 Counter',
        'description': 'Flip-flop circuit dividing input frequency by 2',
        'category': 'digital-sequential',
        'keywords': ['frequency divider', 'divide by 2', 'flip-flop', 'digital']
    },
    'divideby3': {
        'name': 'Divide-by-3 Counter',
        'description': 'Sequential counter dividing frequency by 3',
        'category': 'digital-sequential',
        'keywords': ['frequency divider', 'divide by 3', 'counter', 'digital']
    },
    'dram': {
        'name': 'Dynamic RAM Cell',
        'description': 'Basic DRAM cell showing charge storage and refresh',
        'category': 'digital-memory',
        'keywords': ['DRAM', 'memory cell', 'storage', 'digital']
    },
    'dtlinverter': {
        'name': 'DTL Inverter',
        'description': 'Diode-transistor logic NOT gate',
        'category': 'digital-dtl',
        'keywords': ['DTL', 'inverter', 'logic gate']
    },
    'dtlnand': {
        'name': 'DTL NAND Gate',
        'description': 'NAND gate built using diode-transistor logic',
        'category': 'digital-dtl',
        'keywords': ['DTL', 'NAND gate', 'logic gate']
    },
    'dtlnor': {
        'name': 'DTL NOR Gate',
        'description': 'NOR gate built using diode-transistor logic',
        'category': 'digital-dtl',
        'keywords': ['DTL', 'NOR gate', 'logic gate']
    },
    'eclnor': {
        'name': 'ECL NOR Gate',
        'description': 'Emitter-coupled logic NOR gate',
        'category': 'digital-ecl',
        'keywords': ['ECL', 'NOR gate', 'emitter coupled logic']
    },
    'eclosc': {
        'name': 'ECL Oscillator',
        'description': 'Oscillator built using emitter-coupled logic circuit',
        'category': 'digital-ecl',
        'keywords': ['ECL', 'oscillator', 'emitter coupled logic']
    },
    'edgedff': {
        'name': 'Edge-Triggered D Flip-Flop',
        'description': 'D-type flip-flop triggered on clock edges',
        'category': 'digital-sequential',
        'keywords': ['edge triggered', 'D flip-flop', 'sequential', 'digital']
    },
    'filt-hipass-l': {
        'name': 'High-Pass Filter (Inductor-based)',
        'description': 'First-order LC high-pass filter',
        'category': 'analog-filters',
        'keywords': ['high-pass', 'filter', 'inductor', 'analog']
    },
    'filt-hipass': {
        'name': 'High-Pass Filter (RC)',
        'description': 'First-order RC high-pass filter',
        'category': 'analog-filters',
        'keywords': ['high-pass', 'filter', 'RC', 'analog']
    },
    'filt-lopass-l': {
        'name': 'Low-Pass Filter (Inductor-based)',
        'description': 'First-order LC low-pass filter',
        'category': 'analog-filters',
        'keywords': ['low-pass', 'filter', 'inductor', 'analog']
    },
    'filt-lopass': {
        'name': 'Low-Pass Filter (RC)',
        'description': 'First-order RC low-pass filter',
        'category': 'analog-filters',
        'keywords': ['low-pass', 'filter', 'RC', 'analog']
    },
    'filt-vcvs-hipass': {
        'name': 'High-Pass Filter (VCVS)',
        'description': 'Active high-pass filter using voltage-controlled voltage source',
        'category': 'analog-filters',
        'keywords': ['VCVS', 'high-pass', 'active filter']
    },
    'filt-vcvs-lopass': {
        'name': 'Low-Pass Filter (VCVS)',
        'description': 'Active low-pass filter using voltage-controlled voltage source',
        'category': 'analog-filters',
        'keywords': ['VCVS', 'low-pass', 'active filter']
    },
    'flashadc': {
        'name': 'Flash ADC',
        'description': 'Parallel comparator-based high-speed analog-to-digital converter',
        'category': 'data-conversion',
        'keywords': ['flash ADC', 'analog to digital', 'comparator', 'data converter']
    },
    'follower': {
        "name": "Emitter Follower (Voltage Buffer)",
        "description": "Common-collector BJT amplifier providing unity voltage gain and low output impedance",
        "category": "bjt-amplifiers",
        "keywords": ["emitter follower", "voltage buffer", "BJT", "amplifier"]
    },
    'freqdouble': {
        'name': 'Frequency Doubler',
        'description': 'Analog circuit that doubles the input frequency',
        'category': 'signal-processing',
        'keywords': ['frequency doubler', 'analog', 'wave shaping']
    },
    'fulladd': {
        'name': 'Full Adder',
        'description': '1-bit full adder with carry input and output',
        'category': 'digital-arithmetic',
        'keywords': ['full adder', 'adder', '1-bit', 'sum', 'carry', 'digital']
    },
    'fullrect': {
        'name': 'Full-Wave Rectifier',
        'description': 'Diode-based full-wave rectifier circuit',
        'category': 'analog-rectifiers',
        'keywords': ['rectifier', 'full-wave', 'diode', 'analog']
    },
    'fullrectf': {
        'name': 'Full-Wave Rectifier (Filtered)',
        'description': 'Full-wave rectifier with filter capacitor for DC output',
        'category': 'analog-rectifiers',
        'keywords': ['rectifier', 'full-wave', 'filtered', 'analog']
    },
    'graycode': {
        'name': 'Gray Code Generator',
        'description': 'Generates Gray code sequence from binary counter',
        'category': 'digital-sequential',
        'keywords': ['Gray code', 'counter', 'binary', 'sequential', 'digital']
    },
    'grid': {
        'name': 'Grid Circuit Example',
        'description': 'Demonstrates a basic grid layout or mesh network of resistors',
        'category': 'passive-networks',
        'keywords': ['grid', 'resistor network', 'mesh', 'circuit layout']
    },
    'grid2': {
        'name': 'Grid Circuit Example 2',
        'description': 'Extended grid or lattice network demonstration',
        'category': 'passive-networks',
        'keywords': ['grid', 'network', 'lattice', 'passive']
    },
    'gyrator': {
        'name': 'Gyrator Circuit',
        'description': 'Simulates inductance using op-amps and capacitors',
        'category': 'analog-active',
        'keywords': ['gyrator', 'op-amp', 'simulated inductor', 'analog']
    },
    'halfadd': {
        'name': 'Half Adder',
        'description': '1-bit half adder circuit without carry input',
        'category': 'digital-arithmetic',
        'keywords': ['half adder', 'adder', 'sum', 'logic', 'digital']
    },
    'hartley': {
        'name': 'Hartley Oscillator',
        'description': 'LC oscillator using Hartley configuration',
        'category': 'oscillators',
        'keywords': ['Hartley oscillator', 'LC', 'analog', 'frequency']
    },
    'hfadc': {
        "name": "Flash ADC (High-Speed Analog-to-Digital Converter)",
        "description": "High-speed flash ADC using parallel comparators and resistor reference ladder",
        "category": "data-conversion",
        "keywords": [
            "ADC",
            "flash ADC",
            "comparator ladder",
            "data converter",
            "high speed"
        ]
    },
    'howland': {
        'name': 'Howland Current Pump',
        'description': 'Precision voltage-controlled current source (VCCS)',
        'category': 'analog-active',
        'keywords': ['Howland circuit', 'VCCS', 'current source', 'op-amp']
    },
    'impedance': {
        'name': 'Impedance Measurement Circuit',
        'description': 'Circuit used for measuring complex impedance',
        'category': 'measurement-circuits',
        'keywords': ['impedance', 'measurement', 'analog']
    },
    'indmultfreq': {
        "name": "Inductor Frequency Response",
        "description": "Demonstrates the frequency-dependent behavior of inductors in AC circuits",
        "category": "passive-components",
        "keywords": [
            "inductor",
            "frequency response",
            "reactance",
            "AC"
        ]
    },
    'indmultind': {
        "name": "Inductance Variation Demonstration",
        "description": "Shows how inductance value affects current and voltage behavior in simple RL circuits",
        "category": "passive-components",
        "keywords": [
            "inductance",
            "inductor",
            "RL circuit",
            "analog"
        ]
    },
    'indpar': {
        'name': 'Inductors in Parallel',
        'description': 'Demonstrates equivalent inductance for parallel inductors',
        'category': 'passive-components',
        'keywords': ['inductor', 'parallel', 'equivalent inductance']
    },
    'indseries': {
        'name': 'Inductors in Series',
        'description': 'Demonstrates equivalent inductance for series inductors',
        'category': 'passive-components',
        'keywords': ['inductor', 'series', 'equivalent inductance']
    },
    'induct': {
        'name': 'Basic Inductor Demonstration',
        'description': 'Simple inductor behavior demonstration circuit',
        'category': 'passive-components',
        'keywords': ['inductor', 'magnetism', 'passive', 'coil']
    },
    'inductac': {
        'name': 'AC Inductor Response',
        'description': 'Demonstrates inductor behavior under AC conditions',
        'category': 'passive-components',
        'keywords': ['inductor', 'AC response', 'reactance']
    },
    'inductkick-block': {
        'name': 'Inductive Kickback (Blocked)',
        'description': 'Demonstrates inductive kickback suppression with protective diodes',
        'category': 'analog-transients',
        'keywords': ['inductive kickback', 'protection', 'diode', 'transient']
    },
    'inductkick-snub': {
        'name': 'Inductive Kickback Snubber',
        'description': 'Uses RC snubber network to suppress inductive transients',
        'category': 'analog-transients',
        'keywords': ['inductive kickback', 'snubber', 'RC', 'transient']
    },
    'inductkick': {
        'name': 'Inductive Kickback Demonstration',
        'description': 'Shows voltage spike behavior from inductive load switching',
        'category': 'analog-transients',
        'keywords': ['inductive kickback', 'transient', 'inductor']
    },
    'inv-osc': {
        'name': 'Inverter Oscillator',
        'description': 'Oscillator using digital inverters with feedback',
        'category': 'oscillators',
        'keywords': ['inverter oscillator', 'digital', 'oscillation']
    },
    'invertamp': {
        'name': 'Inverting Amplifier',
        'description': 'Op-amp configured as an inverting amplifier',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'inverting amplifier', 'gain']
    },
    'itov': {
        'name': 'Current-to-Voltage Converter (Transimpedance)',
        'description': 'Converts input current to proportional voltage using op-amp',
        'category': 'signal-converters',
        'keywords': ['current to voltage', 'transimpedance', 'op-amp']
    },
    'jfetamp': {
        'name': 'JFET Amplifier',
        'description': 'Common source JFET amplifier configuration',
        'category': 'fet-amplifiers',
        'keywords': ['JFET', 'amplifier', 'analog']
    },
    'jfetcurrentsrc': {
        'name': 'JFET Current Source',
        'description': 'Constant current source using JFET transistor',
        'category': 'fet-circuits',
        'keywords': ['JFET', 'current source', 'analog']
    },
    'jfetfollower-nooff': {
        'name': 'JFET Source Follower (No Offset)',
        'description': 'JFET buffer circuit with minimized offset voltage',
        'category': 'fet-circuits',
        'keywords': ['JFET', 'source follower', 'buffer']
    },
    'jfetfollower': {
        'name': 'JFET Source Follower',
        'description': 'JFET configured as voltage follower (buffer)',
        'category': 'fet-circuits',
        'keywords': ['JFET', 'source follower', 'buffer']
    },
    'jkff': {
        'name': 'JK Flip-Flop',
        'description': 'Basic JK flip-flop with clock input',
        'category': 'digital-sequential',
        'keywords': ['JK flip-flop', 'sequential', 'digital']
    },
    'johnsonctr': {
        'name': 'Johnson Counter',
        'description': 'Johnson (twisted ring) counter circuit',
        'category': 'digital-sequential',
        'keywords': ['Johnson counter', 'ring counter', 'sequential']
    },
    'ladder': {
        "name": "RC-L Ladder Network",
        "description": "Demonstrates multi-section ladder network behavior using resistors, capacitors, and inductors",
        "category": "analog-filters",
        "keywords": [
            "ladder network",
            "filter",
            "RC",
            "inductor",
            "analog"
        ]
    },
    'leadingedge': {
        'name': 'Leading Edge Detector',
        'description': 'Detects leading edge of pulse waveforms',
        'category': 'signal-processing',
        'keywords': ['edge detector', 'leading edge', 'pulse']
    },
    'ledflasher': {
        'name': 'LED Flasher',
        'description': 'Simple LED flasher using timer or multivibrator',
        'category': 'timers-555',
        'keywords': ['LED flasher', 'timer', 'oscillator']
    },
    'lissa': {
        'name': 'Lissajous Figures Generator',
        'description': 'Generates Lissajous patterns using phase-shifted signals',
        'category': 'signal-generators',
        'keywords': ['Lissajous', 'oscilloscope', 'phase', 'waveform']
    },
    'logconvert': {
        "name": "Logarithmic Amplifier",
        "description": "Op-amp based logarithmic amplifier using diode and transistor feedback network",
        "category": "analog-math",
        "keywords": [
            "log amplifier",
            "log converter",
            "analog computing",
            "transistor",
            "op-amp"
        ]
    },
    'longdist': {
        'name': 'Long Distance Transmission Model',
        'description': 'Simulates signal transmission and loss over long distance line',
        'category': 'communication-circuits',
        'keywords': ['transmission line', 'signal loss', 'communication']
    },
    'lrc-critical': {
        'name': 'LRC Circuit (Critical Damping)',
        'description': 'Critically damped LRC network demonstration',
        'category': 'analog-filters',
        'keywords': ['LRC', 'critical damping', 'filter']
    },
    'lrc': {
        'name': 'LRC Resonant Circuit',
        'description': 'Demonstrates resonance in LRC network',
        'category': 'analog-filters',
        'keywords': ['LRC', 'resonance', 'filter']
    },
    'majority': {
        'name': 'Majority Logic Gate',
        'description': 'Outputs logic 1 if majority of inputs are 1',
        'category': 'digital-logic-gates',
        'keywords': ['majority gate', 'logic', 'digital']
    },
    'masterslaveff': {
        'name': 'Master-Slave Flip-Flop',
        'description': 'D flip-flop using master-slave configuration',
        'category': 'digital-sequential',
        'keywords': ['master-slave flip-flop', 'D flip-flop', 'digital']
    },
    'mirror': {
        'name': 'Current Mirror',
        'description': 'Two-transistor current mirror circuit',
        'category': 'analog-active',
        'keywords': ['current mirror', 'BJT', 'analog']
    },
    'moscurrentramp': {
        "name": "MOSFET Voltage Ramp Generator",
        "description": "Generates a linear voltage ramp using a MOSFET, capacitor, and switch control",
        "category": "fet-circuits",
        "keywords": [
            "MOSFET",
            "ramp generator",
            "voltage ramp",
            "analog"
        ]
    },
    'moscurrentsrc': {
        'name': 'MOSFET Current Source',
        'description': 'Constant current source using MOSFET transistor',
        'category': 'fet-circuits',
        'keywords': ['MOSFET', 'current source', 'analog']
    },
    'mosfetamp': {
        'name': 'MOSFET Amplifier',
        'description': 'Common source MOSFET amplifier',
        'category': 'fet-amplifiers',
        'keywords': ['MOSFET', 'amplifier', 'common source']
    },
    'mosfollower': {
        'name': 'MOSFET Source Follower',
        'description': 'MOSFET configured as a voltage follower (buffer)',
        'category': 'fet-circuits',
        'keywords': ['MOSFET', 'source follower', 'buffer']
    },
    'mosmirror': {
        'name': 'MOSFET Current Mirror',
        'description': 'Current mirror circuit implemented with MOSFETs',
        'category': 'fet-circuits',
        'keywords': ['MOSFET', 'current mirror', 'analog']
    },
    'mosswitch': {
        'name': 'MOSFET Switch',
        'description': 'MOSFET used as an electronic switch',
        'category': 'fet-circuits',
        'keywords': ['MOSFET', 'switch', 'digital', 'analog']
    },
    'mr-crossbar': {
        'name': 'Memristor Crossbar Array',
        'description': 'Crossbar network using memristors for memory or logic',
        'category': 'memristor-circuits',
        'keywords': ['memristor', 'crossbar', 'neuromorphic', 'memory']
    },
    'mr-sine': {
        'name': 'Memristor Sine Response',
        'description': 'Demonstrates sinusoidal input response in memristor',
        'category': 'memristor-circuits',
        'keywords': ['memristor', 'sine', 'analog']
    },
    'mr-sine2': {
        'name': 'Memristor Sine Response 2',
        'description': 'Alternate configuration for sine input response',
        'category': 'memristor-circuits',
        'keywords': ['memristor', 'sine', 'variant']
    },
    'mr-sine3': {
        'name': 'Memristor Sine Response 3',
        'description': 'Third configuration for sine input response in memristor',
        'category': 'memristor-circuits',
        'keywords': ['memristor', 'sine', 'test']
    },
    'mr-square': {
        'name': 'Memristor Square Wave Response',
        'description': 'Memristor response to square wave input',
        'category': 'memristor-circuits',
        'keywords': ['memristor', 'square wave', 'analog']
    },
    'mr-triangle': {
        'name': 'Memristor Triangle Wave Response',
        'description': 'Memristor response to triangular waveform input',
        'category': 'memristor-circuits',
        'keywords': ['memristor', 'triangle wave', 'analog']
    },
    'mr': {
        'name': 'Memristor Basic Model',
        'description': 'Simple memristor demonstration showing resistance change with charge',
        'category': 'memristor-circuits',
        'keywords': ['memristor', 'resistance', 'analog', 'memory']
    },
    'multivib-a': {
        'name': 'Astable Multivibrator',
        'description': 'Free-running multivibrator generating continuous square waves',
        'category': 'oscillators',
        'keywords': ['astable multivibrator', 'square wave', 'oscillator', 'transistor']
    },
    'multivib-bi': {
        'name': 'Bistable Multivibrator (Flip-Flop)',
        'description': 'Two stable-state transistor flip-flop circuit',
        'category': 'digital-sequential',
        'keywords': ['bistable multivibrator', 'flip-flop', 'sequential']
    },
    'multivib-mono': {
        "name": "Monostable Multivibrator (Transistor)",
        "description": "One-shot pulse generator using a bistable transistor pair and coupling capacitor",
        "category": "bjt-multivibrators",
        "keywords": [
            "monostable multivibrator",
            "one-shot",
            "pulse generator",
            "transistor"
        ]
    },
    'mux': {
        'name': '2:1 CMOS Multiplexer',
        'description': '2-to-1 data selector circuit',
        'category': 'digital-combinational',
        'keywords': ['multiplexer', '2:1 cmos mux', 'selector', 'digital']
    },
    'mux3state': {
        'name': '3-State Multiplexer',
        'description': 'Multiplexer with high-impedance state outputs',
        'category': 'digital-combinational',
        'keywords': ['multiplexer', '3-state', 'digital', 'selector']
    },
    'nandff': {
        'name': 'NAND Flip-Flop',
        'description': 'Basic SR flip-flop constructed from NAND gates',
        'category': 'digital-sequential',
        'keywords': ['NAND flip-flop', 'SR latch', 'digital', 'logic']
    },
    'nic-r': {
        'name': 'Negative Impedance Converter (Resistive)',
        'description': 'Op-amp based negative impedance converter using resistors',
        'category': 'analog-active',
        'keywords': ['negative impedance converter', 'NIC', 'op-amp']
    },
    'nmosfet': {
        'name': 'NMOS Transistor',
        'description': 'Basic NMOS transistor example circuit',
        'category': 'fet-devices',
        'keywords': ['NMOS', 'transistor', 'MOSFET', 'device']
    },
    'nmosinverter': {
        'name': 'NMOS Inverter',
        'description': 'NMOS transistor-based inverter circuit',
        'category': 'digital-cmos',
        'keywords': ['NMOS', 'inverter', 'digital logic']
    },
    'nmosinverter2': {
        'name': 'NMOS Inverter (Alternate)',
        'description': 'Alternate NMOS inverter configuration with load resistor',
        'category': 'digital-cmos',
        'keywords': ['NMOS', 'inverter', 'digital']
    },
    'nmosnand': {
        'name': 'NMOS NAND Gate',
        'description': 'NAND logic gate built using NMOS transistors',
        'category': 'digital-cmos',
        'keywords': ['NMOS', 'NAND gate', 'logic', 'digital']
    },
    'norton': {
        "name": "Norton Equivalent Circuit",
        "description": "Demonstrates conversion between current source with parallel resistance and its Norton equivalent form",
        "category": "circuit-theorems",
        "keywords": [
            "Norton equivalent",
            "current source",
            "resistor network",
            "circuit theorem"
        ]
    },
    'notch': {
        'name': 'Notch Filter',
        'description': 'Band-stop filter attenuating specific frequency',
        'category': 'analog-filters',
        'keywords': ['notch filter', 'band-stop', 'analog']
    },
    'npn': {
        'name': 'NPN Transistor',
        'description': 'Basic NPN transistor configuration',
        'category': 'bjt-devices',
        'keywords': ['NPN', 'BJT', 'transistor', 'device']
    },
    'ohms': {
        'name': 'Ohm’s Law Demonstration',
        'description': 'Simple circuit demonstrating voltage-current relationship',
        'category': 'basics',
        'keywords': ['Ohm’s law', 'resistor', 'voltage', 'current']
    },
    'opamp-regulator': {
        'name': 'Op-Amp Voltage Regulator',
        'description': 'Op-amp based linear voltage regulator circuit',
        'category': 'power-supplies',
        'keywords': ['op-amp', 'regulator', 'power supply']
    },
    'opamp': {
        'name': 'Operational Amplifier Model',
        'description': 'Generic op-amp configuration for analog applications',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'amplifier', 'analog']
    },
    'opampfeedback': {
        'name': 'Op-Amp Feedback Demonstration',
        'description': 'Shows positive and negative feedback effects in op-amps',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'feedback', 'stability']
    },
    'opint-current': {
        'name': 'Integrator (Current Input)',
        'description': 'Op-amp integrator taking current input',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'integrator', 'current']
    },
    'opint-invert-amp': {
        'name': 'Op-Amp Inverting Integrator',
        'description': 'Inverting op-amp integrator circuit',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'integrator', 'inverting']
    },
    'opint-slew': {
        'name': 'Op-Amp Slew Rate Demonstration',
        'description': 'Demonstrates op-amp slew rate limitations',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'slew rate', 'transient']
    },
    'opint': {
        'name': 'Op-Amp Integrator',
        'description': 'Standard op-amp integrator circuit',
        'category': 'opamp-circuits',
        'keywords': ['op-amp', 'integrator', 'analog']
    },
    'peak-detect': {
        'name': 'Peak Detector',
        'description': 'Circuit that captures the peak value of an input signal',
        'category': 'analog-signal-conditioning',
        'keywords': ['peak detector', 'analog', 'signal capture']
    },
    'phasecomp': {
        'name': 'Phase Comparator',
        'description': 'Compares phase difference between two signals',
        'category': 'pll-circuits',
        'keywords': ['phase comparator', 'PLL', 'phase detection']
    },
    'phasecompint': {
        'name': 'Phase Comparator with Integrator',
        'description': 'Phase detector with integrated low-pass filter',
        'category': 'pll-circuits',
        'keywords': ['phase comparator', 'PLL', 'integrator']
    },
    'phaseseq': {
        'name': 'Phase Sequence Detector',
        'description': 'Detects phase rotation sequence in three-phase systems',
        'category': 'measurement-circuits',
        'keywords': ['phase sequence', 'three-phase', 'detector']
    },
    'phaseshiftosc': {
        'name': 'Phase Shift Oscillator',
        'description': 'Op-amp based RC phase shift oscillator',
        'category': 'oscillators',
        'keywords': ['phase shift oscillator', 'RC', 'op-amp']
    },
    'phasesplit': {
        "name": "Transistor Phase Splitter",
        "description": "Generates two output signals 180° out of phase using a single transistor and RC network",
        "category": "bjt-amplifiers",
        "keywords": [
            "phase splitter",
            "transistor",
            "amplifier",
            "phase inverter"
        ]
    },
    'pll': {
        'name': 'Phase Locked Loop (PLL)',
        'description': 'Basic PLL circuit with VCO and phase detector',
        'category': 'pll-circuits',
        'keywords': ['PLL', 'phase lock', 'control loop']
    },
    'pll2': {
        'name': 'Phase Locked Loop 2',
        'description': 'Alternate PLL configuration with op-amp components',
        'category': 'pll-circuits',
        'keywords': ['PLL', 'phase lock', 'loop filter']
    },
    'pll2a': {
        'name': 'Phase Locked Loop 2A',
        'description': 'Modified PLL circuit with feedback tuning',
        'category': 'pll-circuits',
        'keywords': ['PLL', 'feedback', 'tuning']
    },
    'pmosfet': {
        'name': 'PMOS Transistor',
        'description': 'Basic PMOS transistor circuit example',
        'category': 'fet-devices',
        'keywords': ['PMOS', 'MOSFET', 'transistor']
    },
    'pnp': {
        'name': 'PNP Transistor',
        'description': 'Basic PNP transistor configuration example',
        'category': 'bjt-devices',
        'keywords': ['PNP', 'BJT', 'transistor']
    },
    'pot': {
        'name': 'Potentiometer',
        'description': 'Variable resistor demonstration circuit',
        'category': 'passive-components',
        'keywords': ['potentiometer', 'variable resistor', 'adjustable']
    },
    'potdivide': {
        'name': 'Potentiometer Divider',
        'description': 'Voltage divider circuit using potentiometer',
        'category': 'passive-components',
        'keywords': ['voltage divider', 'potentiometer', 'resistor']
    },
    'powerfactor1': {
        "name": "Power Factor Correction (Inductive Load)",
        "description": "Demonstrates power factor correction using RL network and reactive compensation",
        "category": "power-circuits",
        "keywords": [
            "power factor",
            "correction",
            "inductive load",
            "AC"
        ]
    },
    'powerfactor2': {
        "name": "Power Factor Correction (LC Network)",
        "description": "Advanced power factor correction circuit using LC compensation for phase balance",
        "category": "power-circuits",
        "keywords": [
            "power factor",
            "correction",
            "LC network",
            "AC"
        ]
    },
    'pushpull': {
        'name': 'Push-Pull Amplifier',
        'description': 'Complementary transistor amplifier for efficient output',
        'category': 'power-amplifiers',
        'keywords': ['push-pull', 'amplifier', 'BJT', 'power']
    },
    'pushpullxover': {
        'name': 'Push-Pull Crossover Amplifier',
        'description': 'Push-pull amplifier with crossover distortion demonstration',
        'category': 'power-amplifiers',
        'keywords': ['push-pull', 'crossover', 'distortion', 'amplifier']
    },
    'r2rladder': {
        'name': 'R-2R Ladder DAC',
        'description': 'Digital-to-analog converter using resistor ladder network',
        'category': 'data-conversion',
        'keywords': ['R-2R', 'DAC', 'ladder', 'digital to analog']
    },
    'rectify': {
        'name': 'Rectifier Demonstration',
        'description': 'Basic diode rectification circuit',
        'category': 'analog-rectifiers',
        'keywords': ['rectifier', 'diode', 'half-wave', 'analog']
    },
    'relaxosc': {
        'name': 'Relaxation Oscillator',
        'description': 'RC relaxation oscillator generating sawtooth waveform',
        'category': 'oscillators',
        'keywords': ['relaxation oscillator', 'RC', 'sawtooth']
    },
    'relay': {
        'name': 'Relay Demonstration',
        'description': 'Basic relay switching circuit',
        'category': 'electromechanical',
        'keywords': ['relay', 'switch', 'coil']
    },
    'relayand': {
        'name': 'Relay AND Gate',
        'description': 'AND logic implemented with relays',
        'category': 'electromechanical',
        'keywords': ['relay', 'AND gate', 'logic']
    },
    'relayctr': {
        "name": "Relay Logic Controller",
        "description": "Complex relay-based control system demonstrating sequential and feedback logic",
        "category": "electromechanical",
        "keywords": [
            "relay",
            "control logic",
            "sequential",
            "feedback"
        ]
    },
    'relayff': {
        'name': 'Relay Flip-Flop',
        'description': 'Bistable relay circuit acting as flip-flop',
        'category': 'electromechanical',
        'keywords': ['relay', 'flip-flop', 'bistable']
    },
    'relaymux': {
        'name': 'Relay Multiplexer',
        'description': 'Multiplexer built using relays',
        'category': 'electromechanical',
        'keywords': ['relay', 'multiplexer', 'selector']
    },
    'relayor': {
        'name': 'Relay OR Gate',
        'description': 'OR logic implemented with relays',
        'category': 'electromechanical',
        'keywords': ['relay', 'OR gate', 'logic']
    },
    'relaytff': {
        'name': 'Relay T Flip-Flop',
        'description': 'Toggle flip-flop built with relay logic',
        'category': 'electromechanical',
        'keywords': ['relay', 'T flip-flop', 'toggle']
    },
    'relayxor': {
        'name': 'Relay XOR Gate',
        'description': 'Exclusive-OR logic implemented with relays',
        'category': 'electromechanical',
        'keywords': ['relay', 'XOR gate', 'logic']
    },
    'res-par': {
        'name': 'Resistors in Parallel',
        'description': 'Parallel resistor combination demonstration',
        'category': 'passive-components',
        'keywords': ['resistor', 'parallel', 'equivalent resistance']
    },
    'res-series': {
        'name': 'Resistors in Series',
        'description': 'Series resistor combination demonstration',
        'category': 'passive-components',
        'keywords': ['resistor', 'series', 'equivalent resistance']
    },
    'resistors': {
        'name': 'Resistor Demonstration',
        'description': 'Basic resistor and ohmic behavior example',
        'category': 'passive-components',
        'keywords': ['resistor', 'Ohm’s law', 'passive']
    },
    'ringing': {
        'name': 'Ringing Circuit',
        'description': 'Demonstrates transient oscillation or ringing in RLC circuit',
        'category': 'analog-transients',
        'keywords': ['ringing', 'RLC', 'transient', 'oscillation']
    },
    'ringmod': {
        'name': 'Ring Modulator',
        'description': 'Analog multiplier circuit for amplitude modulation',
        'category': 'communication-circuits',
        'keywords': ['ring modulator', 'modulation', 'AM', 'analog']
    },
    'rossler': {
        'name': 'Rössler Attractor',
        'description': 'Nonlinear chaotic oscillator (Rössler system)',
        'category': 'chaotic-systems',
        'keywords': ['Rössler', 'chaos', 'oscillator']
    },
    'rtlinverter': {
        'name': 'RTL Inverter',
        'description': 'Resistor-transistor logic NOT gate',
        'category': 'digital-rtl',
        'keywords': ['RTL', 'inverter', 'logic']
    },
    'rtlnand': {
        'name': 'RTL NAND Gate',
        'description': 'Resistor-transistor logic NAND gate',
        'category': 'digital-rtl',
        'keywords': ['RTL', 'NAND gate', 'logic']
    },
    'rtlnor': {
        'name': 'RTL NOR Gate',
        'description': 'Resistor-transistor logic NOR gate',
        'category': 'digital-rtl',
        'keywords': ['RTL', 'NOR gate', 'logic']
    },
    'samplenhold': {
        'name': 'Sample and Hold Circuit',
        'description': 'Captures and holds an analog voltage level',
        'category': 'analog-signal-conditioning',
        'keywords': ['sample and hold', 'analog', 'voltage']
    },
    'sawtooth': {
        'name': 'Sawtooth Wave Generator',
        'description': 'Generates sawtooth waveform using RC charging circuit',
        'category': 'signal-generators',
        'keywords': ['sawtooth', 'waveform', 'generator', 'analog']
    },
    'schmitt': {
        'name': 'Schmitt Trigger',
        'description': 'Comparator circuit with hysteresis',
        'category': 'analog-comparators',
        'keywords': ['Schmitt trigger', 'hysteresis', 'comparator']
    },
    'scr': {
        'name': 'Silicon Controlled Rectifier (SCR)',
        'description': 'Demonstrates SCR triggering and conduction',
        'category': 'power-devices',
        'keywords': ['SCR', 'thyristor', 'switch', 'power']
    },
    'scractrig': {
        'name': 'SCR Trigger Circuit',
        'description': 'Firing circuit for triggering SCR devices',
        'category': 'power-devices',
        'keywords': ['SCR', 'trigger', 'firing circuit']
    },
    'sine': {
        'name': 'Sine Wave Generator',
        'description': 'Analog sine wave oscillator circuit',
        'category': 'signal-generators',
        'keywords': ['sine wave', 'oscillator', 'analog']
    },
    'sinediode': {
        "name": "Diode Wave Shaper Network",
        "description": "Generates sine-like waveform using multiple diode-resistor clipping stages",
        "category": "signal-processing",
        "keywords": [
            "diode shaper",
            "waveform shaping",
            "sine approximation",
            "analog"
        ]
    },
    'spark-marx': {
        'name': 'Marx Generator (Spark)',
        'description': 'High-voltage Marx generator using spark gaps',
        'category': 'high-voltage-circuits',
        'keywords': ['Marx generator', 'spark', 'high voltage']
    },
    'spark-sawtooth': {
        "name": "High Voltage Sawtooth Generator",
        "description": "Generates high-voltage sawtooth waveform using resistor-capacitor charging network",
        "category": "high-voltage-circuits",
        "keywords": [
            "sawtooth",
            "high voltage",
            "RC generator"
        ]
    },
    'spikegen': {
        'name': 'Spike Generator',
        'description': 'Generates narrow pulse spikes from input transitions',
        'category': 'signal-generators',
        'keywords': ['spike generator', 'pulse', 'transient']
    },
    'switchedcap': {
        "name": "Switched-Capacitor Integrator",
        "description": "Demonstrates switched-capacitor integration principle using clocked capacitors and op-amp",
        "category": "analog-filters",
        "keywords": [
            "switched capacitor",
            "integrator",
            "op-amp",
            "analog"
        ]
    },
    'switchfilter': {
        "name": "Switched RC Active Filter",
        "description": "Active filter whose cutoff frequency is controlled by transistor switches",
        "category": "analog-filters",
        "keywords": [
            "switched filter",
            "active filter",
            "RC",
            "analog"
        ]
    },
    'swtreedac': {
        "name": "Switched Binary-Weighted DAC",
        "description": "Digital-to-analog converter using switched binary-weighted resistor network",
        "category": "data-conversion",
        "keywords": [
            "DAC",
            "binary weighted",
            "digital to analog",
            "switching"
        ]
    },
    'synccounter': {
        'name': 'Synchronous Counter',
        'description': 'Binary counter where all flip-flops share the same clock',
        'category': 'digital-sequential',
        'keywords': ['synchronous counter', 'binary', 'digital']
    },
    'tdiode': {
        'name': 'Tunnel Diode',
        'description': 'Demonstrates negative resistance characteristic of tunnel diode',
        'category': 'semiconductor-devices',
        'keywords': ['tunnel diode', 'negative resistance', 'semiconductor']
    },
    'tdosc': {
        'name': 'Tunnel Diode Oscillator',
        'description': 'Oscillator circuit using tunnel diode',
        'category': 'oscillators',
        'keywords': ['tunnel diode', 'oscillator', 'negative resistance']
    },
    'tdrelax': {
        'name': 'Tunnel Diode Relaxation Oscillator',
        'description': 'Relaxation oscillator based on tunnel diode',
        'category': 'oscillators',
        'keywords': ['tunnel diode', 'relaxation', 'oscillator']
    },
    'tesla': {
        'name': 'Tesla Coil',
        'description': 'Resonant transformer circuit producing high voltage',
        'category': 'high-voltage-circuits',
        'keywords': ['Tesla coil', 'resonant transformer', 'high voltage']
    },
    'thevenin': {
        'name': 'Thevenin Equivalent Circuit',
        'description': 'Demonstrates Thevenin equivalent resistance and voltage',
        'category': 'basics',
        'keywords': ['Thevenin theorem', 'equivalent circuit']
    },
    'tl': {
        'name': 'Transmission Line',
        'description': 'Basic lossless transmission line model',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'wave propagation', 'signal']
    },
    'tlfreq': {
        'name': 'Transmission Line Frequency Response',
        'description': 'Shows frequency-dependent behavior of transmission lines',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'frequency response']
    },
    'tllight': {
        'name': 'Transmission Line with Light Speed Delay',
        'description': 'Simulates signal propagation at light speed in a line',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'delay', 'signal']
    },
    'tllopass': {
        'name': 'Transmission Line Low-Pass Filter',
        'description': 'Low-pass behavior modeled with transmission line sections',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'low-pass', 'filter']
    },
    'tlmatch1': {
        'name': 'Transmission Line Matching 1',
        'description': 'Demonstrates impedance matching on transmission line',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'impedance matching']
    },
    'tlmatch2': {
        'name': 'Transmission Line Matching 2',
        'description': 'Alternate impedance matching setup for transmission line',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'matching', 'impedance']
    },
    'tlmis1': {
        'name': 'Transmission Line Mismatch 1',
        'description': 'Demonstrates reflection due to line mismatch',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'reflection', 'mismatch']
    },
    'tlmismatch': {
        'name': 'Transmission Line Mismatch',
        'description': 'Shows mismatched impedance effects in transmission line',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'reflection', 'mismatch']
    },
    'tlstand': {
        'name': 'Transmission Line Standing Wave',
        'description': 'Demonstrates standing wave formation on transmission line',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'standing wave', 'reflection']
    },
    'tlterm': {
        'name': 'Transmission Line Termination',
        'description': 'Properly terminated transmission line example',
        'category': 'transmission-lines',
        'keywords': ['transmission line', 'termination', 'impedance']
    },
    'traffic': {
        'name': 'Traffic Light Controller',
        'description': 'Sequential logic circuit controlling traffic lights',
        'category': 'digital-sequential',
        'keywords': ['traffic light', 'controller', 'sequential logic']
    },
    'trans-diffamp-common': {
        'name': 'Differential Amplifier (Common Source)',
        'description': 'Differential amplifier using FET common-source configuration',
        'category': 'fet-amplifiers',
        'keywords': ['differential amplifier', 'FET', 'common source']
    },
    'trans-diffamp-cursrc': {
        'name': 'Differential Amplifier with Current Source',
        'description': 'Differential amplifier using active current source bias',
        'category': 'fet-amplifiers',
        'keywords': ['differential amplifier', 'current source', 'FET']
    },
    'trans-diffamp': {
        'name': 'Transistor Differential Amplifier',
        'description': 'Differential pair using BJTs',
        'category': 'bjt-amplifiers',
        'keywords': ['BJT', 'differential pair', 'amplifier']
    },
    'transformer': {
        'name': 'Transformer',
        'description': 'Basic transformer model showing coupling between coils',
        'category': 'magnetics',
        'keywords': ['transformer', 'mutual inductance', 'coupling']
    },
    'transformerdc': {
        'name': 'Transformer DC Analysis',
        'description': 'Shows behavior of transformer under DC bias',
        'category': 'magnetics',
        'keywords': ['transformer', 'DC', 'core saturation']
    },
    'transformerdown': {
        'name': 'Step-Down Transformer',
        'description': 'Transformer reducing voltage ratio',
        'category': 'magnetics',
        'keywords': ['transformer', 'step-down', 'voltage']
    },
    'transformerup': {
        'name': 'Step-Up Transformer',
        'description': 'Transformer increasing voltage ratio',
        'category': 'magnetics',
        'keywords': ['transformer', 'step-up', 'voltage']
    },
    'transswitch': {
        'name': 'Transistor Switch',
        'description': 'Transistor used as an on-off switch',
        'category': 'bjt-switching',
        'keywords': ['transistor switch', 'BJT', 'digital']
    },
    'triangle': {
        'name': 'Triangle Wave Generator',
        'description': 'Generates a triangle waveform using integrator and comparator',
        'category': 'signal-generators',
        'keywords': ['triangle wave', 'generator', 'analog']
    },
    'triode': {
        'name': 'Vacuum Triode Device',
        'description': 'Basic triode tube model circuit',
        'category': 'vacuum-tube-circuits',
        'keywords': ['triode', 'vacuum tube', 'amplifier']
    },
    'triodeamp': {
        'name': 'Triode Amplifier',
        'description': 'Vacuum tube amplifier using triode',
        'category': 'vacuum-tube-circuits',
        'keywords': ['triode', 'amplifier', 'vacuum tube']
    },
    'ttlinverter': {
        'name': 'TTL Inverter',
        'description': 'Transistor-transistor logic NOT gate',
        'category': 'digital-ttl',
        'keywords': ['TTL', 'inverter', 'logic']
    },
    'ttlnand': {
        'name': 'TTL NAND Gate',
        'description': 'NAND gate built using TTL logic',
        'category': 'digital-ttl',
        'keywords': ['TTL', 'NAND gate', 'logic']
    },
    'ttlnor': {
        'name': 'TTL NOR Gate',
        'description': 'NOR gate built using TTL logic',
        'category': 'digital-ttl',
        'keywords': ['TTL', 'NOR gate', 'logic']
    },
    'twint': {
        'name': 'Twin-T Notch Filter',
        'description': 'Twin-T RC network creating notch filter response',
        'category': 'analog-filters',
        'keywords': ['Twin-T', 'notch filter', 'analog']
    },
    'vco': {
        'name': 'Voltage Controlled Oscillator (VCO)',
        'description': 'Generates frequency proportional to control voltage',
        'category': 'signal-generators',
        'keywords': ['VCO', 'oscillator', 'voltage control']
    },
    'voltdivide': {
        'name': 'Voltage Divider',
        'description': 'Basic resistor voltage divider circuit',
        'category': 'passive-components',
        'keywords': ['voltage divider', 'resistor', 'passive']
    },
    'voltdouble': {
        'name': 'Voltage Doubler',
        'description': 'Doubles DC output voltage using diodes and capacitors',
        'category': 'power-circuits',
        'keywords': ['voltage doubler', 'rectifier', 'multiplier']
    },
    'voltdouble2': {
        'name': 'Voltage Doubler 2',
        'description': 'Alternative voltage doubler circuit configuration',
        'category': 'power-circuits',
        'keywords': ['voltage doubler', 'rectifier', 'multiplier']
    },
    'voltinvert': {
        'name': 'Voltage Inverter',
        'description': 'Generates negative voltage from positive supply',
        'category': 'power-circuits',
        'keywords': ['voltage inverter', 'charge pump', 'negative voltage']
    },
    'voltquad': {
        'name': 'Voltage Quadrupler',
        'description': 'Multiplies input voltage by four using diode-capacitor stages',
        'category': 'power-circuits',
        'keywords': ['voltage quadrupler', 'multiplier', 'rectifier']
    },
    'volttriple': {
        'name': 'Voltage Tripler',
        'description': 'Multiplies input voltage by three using diode-capacitor network',
        'category': 'power-circuits',
        'keywords': ['voltage tripler', 'rectifier', 'multiplier']
    },
    'volume': {
        'name': 'Volume Control Circuit',
        'description': 'Adjustable audio attenuation circuit',
        'category': 'audio-circuits',
        'keywords': ['volume control', 'attenuator', 'audio']
    },
    'wheatstone': {
        'name': 'Wheatstone Bridge',
        'description': 'Bridge circuit for resistance measurement',
        'category': 'measurement-circuits',
        'keywords': ['Wheatstone bridge', 'resistance', 'measurement']
    },
    'xor': {
        'name': 'XOR Gate',
        'description': 'Exclusive OR logic gate',
        'category': 'digital-logic-gates',
        'keywords': ['XOR', 'logic gate', 'digital']
    },
    'xorphasedet': {
        'name': 'XOR Phase Detector',
        'description': 'Phase detector implemented using XOR logic gate',
        'category': 'pll-circuits',
        'keywords': ['XOR', 'phase detector', 'PLL']
    },
    'zeneriv': {
        'name': 'Zener Diode IV Characteristic',
        'description': 'Plots current-voltage curve of zener diode',
        'category': 'semiconductor-devices',
        'keywords': ['zener diode', 'IV curve', 'breakdown']
    },
    'zenerref': {
        'name': 'Zener Reference Circuit',
        'description': 'Stable voltage reference using zener diode',
        'category': 'power-circuits',
        'keywords': ['zener', 'reference', 'voltage']
    },
    'zenerreffollow': {
        'name': 'Zener Reference Follower',
        'description': 'Buffered zener voltage reference circuit',
        'category': 'power-circuits',
        'keywords': ['zener', 'buffer', 'reference']
    }
}

def get_circuit_metadata(filename):
    """Get metadata for a circuit file, with fallback"""
    if filename in CIRCUIT_METADATA:
        return CIRCUIT_METADATA[filename]
    else:
        return {
            'name': filename.replace('-', ' ').replace('_', ' ').title(),
            'description': f'{filename} circuit from Falstad simulator',
            'category': 'general',
            'keywords': [filename.replace('-', ' '), 'circuit']
        }
