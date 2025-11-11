// war/lib/avr8/avr-bridge.js
// Proper bridge between GWT/JSNI and avr8js library

(function (global) {
  // Check if avr8js is available
  if (!global.avr8js) {
    console.error("avr8js library not found. Make sure avr8js.umd.js is loaded first.");
    return;
  }

  const { CPU, AVRIOPort, AVRUSART, AVREeprom, AVRTimer, portBConfig, portCConfig, portDConfig } = global.avr8js;

  function create(opts) {
    const clockHz = opts.clockHz || 16000000;
    
    // Create CPU instance
    const cpu = new CPU(new Uint16Array(0x8000)); // 32KB flash for ATmega328p
    
    // Storage for callbacks
    const callbacks = {
      onPortBWrite: null,
      onPortCWrite: null,
      onPortDWrite: null,
      onUsartTx: null,
      onAdcRead: null
    };

    // Create IO ports
    const portB = new AVRIOPort(cpu, portBConfig);
    const portC = new AVRIOPort(cpu, portCConfig);
    const portD = new AVRIOPort(cpu, portDConfig);

    // Create USART
    const usart = new AVRUSART(cpu, {
      rxCompleteInterrupt: 0x24,
      dataRegisterEmptyInterrupt: 0x26,
      txCompleteInterrupt: 0x28
    }, 0xc0); // Base address for USART0

    // Hook up port write callbacks
    portB.addListener((value) => {
      if (callbacks.onPortBWrite) {
        callbacks.onPortBWrite(value);
      }
    });

    portC.addListener((value) => {
      if (callbacks.onPortCWrite) {
        callbacks.onPortCWrite(value);
      }
    });

    portD.addListener((value) => {
      if (callbacks.onPortDWrite) {
        callbacks.onPortDWrite(value);
      }
    });

    // Hook up USART TX
    usart.onByteTransmit = (value) => {
      if (callbacks.onUsartTx) {
        callbacks.onUsartTx(value);
      }
    };

    // ADC reading function (to be called when CPU reads ADC)
    // We'll hook this into the CPU memory when ADC register is read
    const ADC_LOW = 0x78;
    const ADC_HIGH = 0x79;
    const ADCSRA = 0x7a;
    
    let lastAdcChannel = 0;
    
    // Monitor ADC control register writes to detect conversions
    const originalDataWrite = cpu.writeData.bind(cpu);
    cpu.writeData = function(addr, value) {
      originalDataWrite(addr, value);
      
      // Check if starting ADC conversion (ADSC bit set in ADCSRA)
      if (addr === ADCSRA && (value & 0x40)) {
        // Read which channel from ADMUX (0x7c)
        const admux = cpu.data[0x7c];
        lastAdcChannel = admux & 0x07; // Bottom 3 bits = channel
        
        // Get ADC value from callback
        let adcValue = 0;
        if (callbacks.onAdcRead) {
          adcValue = callbacks.onAdcRead(lastAdcChannel);
        }
        
        // Write result to ADC registers
        cpu.data[ADC_LOW] = adcValue & 0xFF;
        cpu.data[ADC_HIGH] = (adcValue >> 8) & 0x03;
        
        // Clear ADSC bit and set ADIF (conversion complete)
        cpu.data[ADCSRA] = (value & ~0x40) | 0x10;
      }
    };

    // Load HEX function
    function loadHex(hexText) {
      const program = parseHex(hexText);
      cpu.progMem.set(program);
      cpu.pc = 0;
      cpu.cycles = 0;
    }

    // Execute cycles
    function step(cycles) {
      for (let i = 0; i < cycles; i++) {
        cpu.tick();
      }
    }

    // Set callbacks
    function setCallbacks(cb) {
      callbacks.onPortBWrite = cb.onPortBWrite || null;
      callbacks.onPortCWrite = cb.onPortCWrite || null;
      callbacks.onPortDWrite = cb.onPortDWrite || null;
      callbacks.onUsartTx = cb.onUsartTx || null;
      callbacks.onAdcRead = cb.onAdcRead || null;
    }

    // Set input bit on a port
    function setInputBit(portName, bit, high) {
      let port;
      switch (portName) {
        case 'B': port = portB; break;
        case 'C': port = portC; break;
        case 'D': port = portD; break;
        default: return;
      }
      
      // Read current PIN value, modify bit, write back
      const pinAddr = port.pinRegister;
      let pinValue = cpu.data[pinAddr];
      
      if (high) {
        pinValue |= (1 << bit);
      } else {
        pinValue &= ~(1 << bit);
      }
      
      cpu.data[pinAddr] = pinValue;
    }

    return {
      cpu,
      portB,
      portC,
      portD,
      usart,
      step,
      loadHex,
      setCallbacks,
      setInputBit,
      clockHz
    };
  }

  // Intel HEX parser
  function parseHex(hex) {
    const lines = hex.split('\n').filter(line => line.trim());
    const program = new Uint8Array(0x8000); // 32KB
    let baseAddress = 0;

    for (const line of lines) {
      if (!line.startsWith(':')) continue;
      
      const bytes = [];
      for (let i = 1; i < line.length; i += 2) {
        bytes.push(parseInt(line.substr(i, 2), 16));
      }
      
      const count = bytes[0];
      const address = (bytes[1] << 8) | bytes[2];
      const recordType = bytes[3];
      
      if (recordType === 0x00) {
        // Data record
        for (let i = 0; i < count; i++) {
          const addr = baseAddress + address + i;
          if (addr < program.length) {
            program[addr] = bytes[4 + i];
          }
        }
      } else if (recordType === 0x02) {
        // Extended segment address
        baseAddress = ((bytes[4] << 8) | bytes[5]) << 4;
      } else if (recordType === 0x04) {
        // Extended linear address
        baseAddress = ((bytes[4] << 8) | bytes[5]) << 16;
      } else if (recordType === 0x01) {
        // End of file
        break;
      }
    }
    
    return program;
  }

  // Export to global
  global.AVRBridge = { create };
  
  console.log("AVRBridge initialized successfully");

})(window);