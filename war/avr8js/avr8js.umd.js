var avr8js = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // node_modules/avr8js/dist/esm/index.js
  var index_exports = {};
  __export(index_exports, {
    ADCMuxInputType: () => ADCMuxInputType,
    ADCReference: () => ADCReference,
    AVRADC: () => AVRADC,
    AVRClock: () => AVRClock,
    AVREEPROM: () => AVREEPROM,
    AVRIOPort: () => AVRIOPort,
    AVRSPI: () => AVRSPI,
    AVRTWI: () => AVRTWI,
    AVRTimer: () => AVRTimer,
    AVRUSART: () => AVRUSART,
    AVRUSI: () => AVRUSI,
    AVRWatchdog: () => AVRWatchdog,
    CPU: () => CPU,
    EEPROMMemoryBackend: () => EEPROMMemoryBackend,
    INT0: () => INT0,
    INT1: () => INT1,
    NoopTWIEventHandler: () => NoopTWIEventHandler,
    PCINT0: () => PCINT0,
    PCINT1: () => PCINT1,
    PCINT2: () => PCINT2,
    PinState: () => PinState,
    adcConfig: () => adcConfig,
    atmega328Channels: () => atmega328Channels,
    avrInstruction: () => avrInstruction,
    avrInterrupt: () => avrInterrupt,
    clockConfig: () => clockConfig,
    eepromConfig: () => eepromConfig,
    portAConfig: () => portAConfig,
    portBConfig: () => portBConfig,
    portCConfig: () => portCConfig,
    portDConfig: () => portDConfig,
    portEConfig: () => portEConfig,
    portFConfig: () => portFConfig,
    portGConfig: () => portGConfig,
    portHConfig: () => portHConfig,
    portJConfig: () => portJConfig,
    portKConfig: () => portKConfig,
    portLConfig: () => portLConfig,
    spiConfig: () => spiConfig,
    timer0Config: () => timer0Config,
    timer1Config: () => timer1Config,
    timer2Config: () => timer2Config,
    twiConfig: () => twiConfig,
    usart0Config: () => usart0Config,
    watchdogConfig: () => watchdogConfig
  });

  // node_modules/avr8js/dist/esm/cpu/interrupt.js
  function avrInterrupt(cpu, addr) {
    const sp = cpu.dataView.getUint16(93, true);
    cpu.data[sp] = cpu.pc & 255;
    cpu.data[sp - 1] = cpu.pc >> 8 & 255;
    if (cpu.pc22Bits) {
      cpu.data[sp - 2] = cpu.pc >> 16 & 255;
    }
    cpu.dataView.setUint16(93, sp - (cpu.pc22Bits ? 3 : 2), true);
    cpu.data[95] &= 127;
    cpu.cycles += 2;
    cpu.pc = addr;
  }

  // node_modules/avr8js/dist/esm/cpu/cpu.js
  var registerSpace = 256;
  var MAX_INTERRUPTS = 128;
  var CPU = class {
    constructor(progMem, sramBytes = 8192) {
      this.progMem = progMem;
      this.sramBytes = sramBytes;
      this.data = new Uint8Array(this.sramBytes + registerSpace);
      this.data16 = new Uint16Array(this.data.buffer);
      this.dataView = new DataView(this.data.buffer);
      this.progBytes = new Uint8Array(this.progMem.buffer);
      this.readHooks = [];
      this.writeHooks = [];
      this.pendingInterrupts = new Array(MAX_INTERRUPTS);
      this.nextClockEvent = null;
      this.clockEventPool = [];
      this.pc22Bits = this.progBytes.length > 131072;
      this.gpioPorts = /* @__PURE__ */ new Set();
      this.gpioByPort = [];
      this.onWatchdogReset = () => {
      };
      this.pc = 0;
      this.cycles = 0;
      this.nextInterrupt = -1;
      this.maxInterrupt = 0;
      this.reset();
    }
    reset() {
      this.SP = this.data.length - 1;
      this.pc = 0;
      this.pendingInterrupts.fill(null);
      this.nextInterrupt = -1;
      this.nextClockEvent = null;
    }
    readData(addr) {
      if (addr >= 32 && this.readHooks[addr]) {
        return this.readHooks[addr](addr);
      }
      return this.data[addr];
    }
    writeData(addr, value, mask = 255) {
      const hook = this.writeHooks[addr];
      if (hook) {
        if (hook(value, this.data[addr], addr, mask)) {
          return;
        }
      }
      this.data[addr] = value;
    }
    get SP() {
      return this.dataView.getUint16(93, true);
    }
    set SP(value) {
      this.dataView.setUint16(93, value, true);
    }
    get SREG() {
      return this.data[95];
    }
    get interruptsEnabled() {
      return this.SREG & 128 ? true : false;
    }
    setInterruptFlag(interrupt) {
      const { flagRegister, flagMask, enableRegister, enableMask } = interrupt;
      if (interrupt.inverseFlag) {
        this.data[flagRegister] &= ~flagMask;
      } else {
        this.data[flagRegister] |= flagMask;
      }
      if (this.data[enableRegister] & enableMask) {
        this.queueInterrupt(interrupt);
      }
    }
    updateInterruptEnable(interrupt, registerValue) {
      const { enableMask, flagRegister, flagMask, inverseFlag } = interrupt;
      if (registerValue & enableMask) {
        const bitSet = this.data[flagRegister] & flagMask;
        if (inverseFlag ? !bitSet : bitSet) {
          this.queueInterrupt(interrupt);
        }
      } else {
        this.clearInterrupt(interrupt, false);
      }
    }
    queueInterrupt(interrupt) {
      const { address } = interrupt;
      this.pendingInterrupts[address] = interrupt;
      if (this.nextInterrupt === -1 || this.nextInterrupt > address) {
        this.nextInterrupt = address;
      }
      if (address > this.maxInterrupt) {
        this.maxInterrupt = address;
      }
    }
    clearInterrupt({ address, flagRegister, flagMask }, clearFlag = true) {
      if (clearFlag) {
        this.data[flagRegister] &= ~flagMask;
      }
      const { pendingInterrupts, maxInterrupt } = this;
      if (!pendingInterrupts[address]) {
        return;
      }
      pendingInterrupts[address] = null;
      if (this.nextInterrupt === address) {
        this.nextInterrupt = -1;
        for (let i = address + 1; i <= maxInterrupt; i++) {
          if (pendingInterrupts[i]) {
            this.nextInterrupt = i;
            break;
          }
        }
      }
    }
    clearInterruptByFlag(interrupt, registerValue) {
      const { flagRegister, flagMask } = interrupt;
      if (registerValue & flagMask) {
        this.data[flagRegister] &= ~flagMask;
        this.clearInterrupt(interrupt);
      }
    }
    addClockEvent(callback, cycles) {
      const { clockEventPool } = this;
      cycles = this.cycles + Math.max(1, cycles);
      const maybeEntry = clockEventPool.pop();
      const entry = maybeEntry !== null && maybeEntry !== void 0 ? maybeEntry : { cycles, callback, next: null };
      entry.cycles = cycles;
      entry.callback = callback;
      let { nextClockEvent: clockEvent } = this;
      let lastItem = null;
      while (clockEvent && clockEvent.cycles < cycles) {
        lastItem = clockEvent;
        clockEvent = clockEvent.next;
      }
      if (lastItem) {
        lastItem.next = entry;
        entry.next = clockEvent;
      } else {
        this.nextClockEvent = entry;
        entry.next = clockEvent;
      }
      return callback;
    }
    updateClockEvent(callback, cycles) {
      if (this.clearClockEvent(callback)) {
        this.addClockEvent(callback, cycles);
        return true;
      }
      return false;
    }
    clearClockEvent(callback) {
      let { nextClockEvent: clockEvent } = this;
      if (!clockEvent) {
        return false;
      }
      const { clockEventPool } = this;
      let lastItem = null;
      while (clockEvent) {
        if (clockEvent.callback === callback) {
          if (lastItem) {
            lastItem.next = clockEvent.next;
          } else {
            this.nextClockEvent = clockEvent.next;
          }
          if (clockEventPool.length < 10) {
            clockEventPool.push(clockEvent);
          }
          return true;
        }
        lastItem = clockEvent;
        clockEvent = clockEvent.next;
      }
      return false;
    }
    tick() {
      const { nextClockEvent } = this;
      if (nextClockEvent && nextClockEvent.cycles <= this.cycles) {
        nextClockEvent.callback();
        this.nextClockEvent = nextClockEvent.next;
        if (this.clockEventPool.length < 10) {
          this.clockEventPool.push(nextClockEvent);
        }
      }
      const { nextInterrupt } = this;
      if (this.interruptsEnabled && nextInterrupt >= 0) {
        const interrupt = this.pendingInterrupts[nextInterrupt];
        avrInterrupt(this, interrupt.address);
        if (!interrupt.constant) {
          this.clearInterrupt(interrupt);
        }
      }
    }
  };

  // node_modules/avr8js/dist/esm/cpu/instruction.js
  function isTwoWordInstruction(opcode) {
    return (
      /* LDS */
      (opcode & 65039) === 36864 || /* STS */
      (opcode & 65039) === 37376 || /* CALL */
      (opcode & 65038) === 37902 || /* JMP */
      (opcode & 65038) === 37900
    );
  }
  function avrInstruction(cpu) {
    const opcode = cpu.progMem[cpu.pc];
    if ((opcode & 64512) === 7168) {
      const d = cpu.data[(opcode & 496) >> 4];
      const r = cpu.data[opcode & 15 | (opcode & 512) >> 5];
      const sum = d + r + (cpu.data[95] & 1);
      const R = sum & 255;
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 192;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= (R ^ r) & (d ^ R) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= sum & 256 ? 1 : 0;
      sreg |= 1 & (d & r | r & ~R | ~R & d) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 64512) === 3072) {
      const d = cpu.data[(opcode & 496) >> 4];
      const r = cpu.data[opcode & 15 | (opcode & 512) >> 5];
      const R = d + r & 255;
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 192;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= (R ^ r) & (R ^ d) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= d + r & 256 ? 1 : 0;
      sreg |= 1 & (d & r | r & ~R | ~R & d) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 65280) === 38400) {
      const addr = 2 * ((opcode & 48) >> 4) + 24;
      const value = cpu.dataView.getUint16(addr, true);
      const R = value + (opcode & 15 | (opcode & 192) >> 2) & 65535;
      cpu.dataView.setUint16(addr, R, true);
      let sreg = cpu.data[95] & 224;
      sreg |= R ? 0 : 2;
      sreg |= 32768 & R ? 4 : 0;
      sreg |= ~value & R & 32768 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= ~R & value & 32768 ? 1 : 0;
      cpu.data[95] = sreg;
      cpu.cycles++;
    } else if ((opcode & 64512) === 8192) {
      const R = cpu.data[(opcode & 496) >> 4] & cpu.data[opcode & 15 | (opcode & 512) >> 5];
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 225;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 61440) === 28672) {
      const R = cpu.data[((opcode & 240) >> 4) + 16] & (opcode & 15 | (opcode & 3840) >> 4);
      cpu.data[((opcode & 240) >> 4) + 16] = R;
      let sreg = cpu.data[95] & 225;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 65039) === 37893) {
      const value = cpu.data[(opcode & 496) >> 4];
      const R = value >>> 1 | 128 & value;
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 224;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= value & 1;
      sreg |= sreg >> 2 & 1 ^ sreg & 1 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 65423) === 38024) {
      cpu.data[95] &= ~(1 << ((opcode & 112) >> 4));
    } else if ((opcode & 65032) === 63488) {
      const b = opcode & 7;
      const d = (opcode & 496) >> 4;
      cpu.data[d] = ~(1 << b) & cpu.data[d] | (cpu.data[95] >> 6 & 1) << b;
    } else if ((opcode & 64512) === 62464) {
      if (!(cpu.data[95] & 1 << (opcode & 7))) {
        cpu.pc = cpu.pc + (((opcode & 504) >> 3) - (opcode & 512 ? 64 : 0));
        cpu.cycles++;
      }
    } else if ((opcode & 64512) === 61440) {
      if (cpu.data[95] & 1 << (opcode & 7)) {
        cpu.pc = cpu.pc + (((opcode & 504) >> 3) - (opcode & 512 ? 64 : 0));
        cpu.cycles++;
      }
    } else if ((opcode & 65423) === 37896) {
      cpu.data[95] |= 1 << ((opcode & 112) >> 4);
    } else if ((opcode & 65032) === 64e3) {
      const d = cpu.data[(opcode & 496) >> 4];
      const b = opcode & 7;
      cpu.data[95] = cpu.data[95] & 191 | (d >> b & 1 ? 64 : 0);
    } else if ((opcode & 65038) === 37902) {
      const k = cpu.progMem[cpu.pc + 1] | (opcode & 1) << 16 | (opcode & 496) << 13;
      const ret = cpu.pc + 2;
      const sp = cpu.dataView.getUint16(93, true);
      const { pc22Bits } = cpu;
      cpu.data[sp] = 255 & ret;
      cpu.data[sp - 1] = ret >> 8 & 255;
      if (pc22Bits) {
        cpu.data[sp - 2] = ret >> 16 & 255;
      }
      cpu.dataView.setUint16(93, sp - (pc22Bits ? 3 : 2), true);
      cpu.pc = k - 1;
      cpu.cycles += pc22Bits ? 4 : 3;
    } else if ((opcode & 65280) === 38912) {
      const A = opcode & 248;
      const b = opcode & 7;
      const R = cpu.readData((A >> 3) + 32);
      const mask = 1 << b;
      cpu.writeData((A >> 3) + 32, R & ~mask, mask);
    } else if ((opcode & 65039) === 37888) {
      const d = (opcode & 496) >> 4;
      const R = 255 - cpu.data[d];
      cpu.data[d] = R;
      let sreg = cpu.data[95] & 225 | 1;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 64512) === 5120) {
      const val1 = cpu.data[(opcode & 496) >> 4];
      const val2 = cpu.data[opcode & 15 | (opcode & 512) >> 5];
      const R = val1 - val2;
      let sreg = cpu.data[95] & 192;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= 0 !== ((val1 ^ val2) & (val1 ^ R) & 128) ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= val2 > val1 ? 1 : 0;
      sreg |= 1 & (~val1 & val2 | val2 & R | R & ~val1) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 64512) === 1024) {
      const arg1 = cpu.data[(opcode & 496) >> 4];
      const arg2 = cpu.data[opcode & 15 | (opcode & 512) >> 5];
      let sreg = cpu.data[95];
      const r = arg1 - arg2 - (sreg & 1);
      sreg = sreg & 192 | (!r && sreg >> 1 & 1 ? 2 : 0) | (arg2 + (sreg & 1) > arg1 ? 1 : 0);
      sreg |= 128 & r ? 4 : 0;
      sreg |= (arg1 ^ arg2) & (arg1 ^ r) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= 1 & (~arg1 & arg2 | arg2 & r | r & ~arg1) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 61440) === 12288) {
      const arg1 = cpu.data[((opcode & 240) >> 4) + 16];
      const arg2 = opcode & 15 | (opcode & 3840) >> 4;
      const r = arg1 - arg2;
      let sreg = cpu.data[95] & 192;
      sreg |= r ? 0 : 2;
      sreg |= 128 & r ? 4 : 0;
      sreg |= (arg1 ^ arg2) & (arg1 ^ r) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= arg2 > arg1 ? 1 : 0;
      sreg |= 1 & (~arg1 & arg2 | arg2 & r | r & ~arg1) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 64512) === 4096) {
      if (cpu.data[(opcode & 496) >> 4] === cpu.data[opcode & 15 | (opcode & 512) >> 5]) {
        const nextOpcode = cpu.progMem[cpu.pc + 1];
        const skipSize = isTwoWordInstruction(nextOpcode) ? 2 : 1;
        cpu.pc += skipSize;
        cpu.cycles += skipSize;
      }
    } else if ((opcode & 65039) === 37898) {
      const value = cpu.data[(opcode & 496) >> 4];
      const R = value - 1;
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 225;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= 128 === value ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if (opcode === 38169) {
      const retAddr = cpu.pc + 1;
      const sp = cpu.dataView.getUint16(93, true);
      const eind = cpu.data[92];
      cpu.data[sp] = retAddr & 255;
      cpu.data[sp - 1] = retAddr >> 8 & 255;
      cpu.data[sp - 2] = retAddr >> 16 & 255;
      cpu.dataView.setUint16(93, sp - 3, true);
      cpu.pc = (eind << 16 | cpu.dataView.getUint16(30, true)) - 1;
      cpu.cycles += 3;
    } else if (opcode === 37913) {
      const eind = cpu.data[92];
      cpu.pc = (eind << 16 | cpu.dataView.getUint16(30, true)) - 1;
      cpu.cycles++;
    } else if (opcode === 38360) {
      const rampz = cpu.data[91];
      cpu.data[0] = cpu.progBytes[rampz << 16 | cpu.dataView.getUint16(30, true)];
      cpu.cycles += 2;
    } else if ((opcode & 65039) === 36870) {
      const rampz = cpu.data[91];
      cpu.data[(opcode & 496) >> 4] = cpu.progBytes[rampz << 16 | cpu.dataView.getUint16(30, true)];
      cpu.cycles += 2;
    } else if ((opcode & 65039) === 36871) {
      const rampz = cpu.data[91];
      const i = cpu.dataView.getUint16(30, true);
      cpu.data[(opcode & 496) >> 4] = cpu.progBytes[rampz << 16 | i];
      cpu.dataView.setUint16(30, i + 1, true);
      if (i === 65535) {
        cpu.data[91] = (rampz + 1) % (cpu.progBytes.length >> 16);
      }
      cpu.cycles += 2;
    } else if ((opcode & 64512) === 9216) {
      const R = cpu.data[(opcode & 496) >> 4] ^ cpu.data[opcode & 15 | (opcode & 512) >> 5];
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 225;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 65416) === 776) {
      const v1 = cpu.data[((opcode & 112) >> 4) + 16];
      const v2 = cpu.data[(opcode & 7) + 16];
      const R = v1 * v2 << 1;
      cpu.dataView.setUint16(0, R, true);
      cpu.data[95] = cpu.data[95] & 252 | (65535 & R ? 0 : 2) | (v1 * v2 & 32768 ? 1 : 0);
      cpu.cycles++;
    } else if ((opcode & 65416) === 896) {
      const v1 = cpu.dataView.getInt8(((opcode & 112) >> 4) + 16);
      const v2 = cpu.dataView.getInt8((opcode & 7) + 16);
      const R = v1 * v2 << 1;
      cpu.dataView.setInt16(0, R, true);
      cpu.data[95] = cpu.data[95] & 252 | (65535 & R ? 0 : 2) | (v1 * v2 & 32768 ? 1 : 0);
      cpu.cycles++;
    } else if ((opcode & 65416) === 904) {
      const v1 = cpu.dataView.getInt8(((opcode & 112) >> 4) + 16);
      const v2 = cpu.data[(opcode & 7) + 16];
      const R = v1 * v2 << 1;
      cpu.dataView.setInt16(0, R, true);
      cpu.data[95] = cpu.data[95] & 252 | (65535 & R ? 2 : 0) | (v1 * v2 & 32768 ? 1 : 0);
      cpu.cycles++;
    } else if (opcode === 38153) {
      const retAddr = cpu.pc + 1;
      const sp = cpu.dataView.getUint16(93, true);
      const { pc22Bits } = cpu;
      cpu.data[sp] = retAddr & 255;
      cpu.data[sp - 1] = retAddr >> 8 & 255;
      if (pc22Bits) {
        cpu.data[sp - 2] = retAddr >> 16 & 255;
      }
      cpu.dataView.setUint16(93, sp - (pc22Bits ? 3 : 2), true);
      cpu.pc = cpu.dataView.getUint16(30, true) - 1;
      cpu.cycles += pc22Bits ? 3 : 2;
    } else if (opcode === 37897) {
      cpu.pc = cpu.dataView.getUint16(30, true) - 1;
      cpu.cycles++;
    } else if ((opcode & 63488) === 45056) {
      const i = cpu.readData((opcode & 15 | (opcode & 1536) >> 5) + 32);
      cpu.data[(opcode & 496) >> 4] = i;
    } else if ((opcode & 65039) === 37891) {
      const d = cpu.data[(opcode & 496) >> 4];
      const r = d + 1 & 255;
      cpu.data[(opcode & 496) >> 4] = r;
      let sreg = cpu.data[95] & 225;
      sreg |= r ? 0 : 2;
      sreg |= 128 & r ? 4 : 0;
      sreg |= 127 === d ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 65038) === 37900) {
      cpu.pc = (cpu.progMem[cpu.pc + 1] | (opcode & 1) << 16 | (opcode & 496) << 13) - 1;
      cpu.cycles += 2;
    } else if ((opcode & 65039) === 37382) {
      const r = (opcode & 496) >> 4;
      const clear = cpu.data[r];
      const value = cpu.readData(cpu.dataView.getUint16(30, true));
      cpu.writeData(cpu.dataView.getUint16(30, true), value & 255 - clear);
      cpu.data[r] = value;
    } else if ((opcode & 65039) === 37381) {
      const r = (opcode & 496) >> 4;
      const set = cpu.data[r];
      const value = cpu.readData(cpu.dataView.getUint16(30, true));
      cpu.writeData(cpu.dataView.getUint16(30, true), value | set);
      cpu.data[r] = value;
    } else if ((opcode & 65039) === 37383) {
      const r = cpu.data[(opcode & 496) >> 4];
      const R = cpu.readData(cpu.dataView.getUint16(30, true));
      cpu.writeData(cpu.dataView.getUint16(30, true), r ^ R);
      cpu.data[(opcode & 496) >> 4] = R;
    } else if ((opcode & 61440) === 57344) {
      cpu.data[((opcode & 240) >> 4) + 16] = opcode & 15 | (opcode & 3840) >> 4;
    } else if ((opcode & 65039) === 36864) {
      cpu.cycles++;
      const value = cpu.readData(cpu.progMem[cpu.pc + 1]);
      cpu.data[(opcode & 496) >> 4] = value;
      cpu.pc++;
    } else if ((opcode & 65039) === 36876) {
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(cpu.dataView.getUint16(26, true));
    } else if ((opcode & 65039) === 36877) {
      const x = cpu.dataView.getUint16(26, true);
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(x);
      cpu.dataView.setUint16(26, x + 1, true);
    } else if ((opcode & 65039) === 36878) {
      const x = cpu.dataView.getUint16(26, true) - 1;
      cpu.dataView.setUint16(26, x, true);
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(x);
    } else if ((opcode & 65039) === 32776) {
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(cpu.dataView.getUint16(28, true));
    } else if ((opcode & 65039) === 36873) {
      const y = cpu.dataView.getUint16(28, true);
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(y);
      cpu.dataView.setUint16(28, y + 1, true);
    } else if ((opcode & 65039) === 36874) {
      const y = cpu.dataView.getUint16(28, true) - 1;
      cpu.dataView.setUint16(28, y, true);
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(y);
    } else if ((opcode & 53768) === 32776 && opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8) {
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(cpu.dataView.getUint16(28, true) + (opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8));
    } else if ((opcode & 65039) === 32768) {
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(cpu.dataView.getUint16(30, true));
    } else if ((opcode & 65039) === 36865) {
      const z = cpu.dataView.getUint16(30, true);
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(z);
      cpu.dataView.setUint16(30, z + 1, true);
    } else if ((opcode & 65039) === 36866) {
      const z = cpu.dataView.getUint16(30, true) - 1;
      cpu.dataView.setUint16(30, z, true);
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(z);
    } else if ((opcode & 53768) === 32768 && opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8) {
      cpu.cycles++;
      cpu.data[(opcode & 496) >> 4] = cpu.readData(cpu.dataView.getUint16(30, true) + (opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8));
    } else if (opcode === 38344) {
      cpu.data[0] = cpu.progBytes[cpu.dataView.getUint16(30, true)];
      cpu.cycles += 2;
    } else if ((opcode & 65039) === 36868) {
      cpu.data[(opcode & 496) >> 4] = cpu.progBytes[cpu.dataView.getUint16(30, true)];
      cpu.cycles += 2;
    } else if ((opcode & 65039) === 36869) {
      const i = cpu.dataView.getUint16(30, true);
      cpu.data[(opcode & 496) >> 4] = cpu.progBytes[i];
      cpu.dataView.setUint16(30, i + 1, true);
      cpu.cycles += 2;
    } else if ((opcode & 65039) === 37894) {
      const value = cpu.data[(opcode & 496) >> 4];
      const R = value >>> 1;
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 224;
      sreg |= R ? 0 : 2;
      sreg |= value & 1;
      sreg |= sreg >> 2 & 1 ^ sreg & 1 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 64512) === 11264) {
      cpu.data[(opcode & 496) >> 4] = cpu.data[opcode & 15 | (opcode & 512) >> 5];
    } else if ((opcode & 65280) === 256) {
      const r2 = 2 * (opcode & 15);
      const d2 = 2 * ((opcode & 240) >> 4);
      cpu.data[d2] = cpu.data[r2];
      cpu.data[d2 + 1] = cpu.data[r2 + 1];
    } else if ((opcode & 64512) === 39936) {
      const R = cpu.data[(opcode & 496) >> 4] * cpu.data[opcode & 15 | (opcode & 512) >> 5];
      cpu.dataView.setUint16(0, R, true);
      cpu.data[95] = cpu.data[95] & 252 | (65535 & R ? 0 : 2) | (32768 & R ? 1 : 0);
      cpu.cycles++;
    } else if ((opcode & 65280) === 512) {
      const R = cpu.dataView.getInt8(((opcode & 240) >> 4) + 16) * cpu.dataView.getInt8((opcode & 15) + 16);
      cpu.dataView.setInt16(0, R, true);
      cpu.data[95] = cpu.data[95] & 252 | (65535 & R ? 0 : 2) | (32768 & R ? 1 : 0);
      cpu.cycles++;
    } else if ((opcode & 65416) === 768) {
      const R = cpu.dataView.getInt8(((opcode & 112) >> 4) + 16) * cpu.data[(opcode & 7) + 16];
      cpu.dataView.setInt16(0, R, true);
      cpu.data[95] = cpu.data[95] & 252 | (65535 & R ? 0 : 2) | (32768 & R ? 1 : 0);
      cpu.cycles++;
    } else if ((opcode & 65039) === 37889) {
      const d = (opcode & 496) >> 4;
      const value = cpu.data[d];
      const R = 0 - value;
      cpu.data[d] = R;
      let sreg = cpu.data[95] & 192;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= 128 === R ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= R ? 1 : 0;
      sreg |= 1 & (R | value) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if (opcode === 0) {
    } else if ((opcode & 64512) === 10240) {
      const R = cpu.data[(opcode & 496) >> 4] | cpu.data[opcode & 15 | (opcode & 512) >> 5];
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 225;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 61440) === 24576) {
      const R = cpu.data[((opcode & 240) >> 4) + 16] | (opcode & 15 | (opcode & 3840) >> 4);
      cpu.data[((opcode & 240) >> 4) + 16] = R;
      let sreg = cpu.data[95] & 225;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 63488) === 47104) {
      cpu.writeData((opcode & 15 | (opcode & 1536) >> 5) + 32, cpu.data[(opcode & 496) >> 4]);
    } else if ((opcode & 65039) === 36879) {
      const value = cpu.dataView.getUint16(93, true) + 1;
      cpu.dataView.setUint16(93, value, true);
      cpu.data[(opcode & 496) >> 4] = cpu.data[value];
      cpu.cycles++;
    } else if ((opcode & 65039) === 37391) {
      const value = cpu.dataView.getUint16(93, true);
      cpu.data[value] = cpu.data[(opcode & 496) >> 4];
      cpu.dataView.setUint16(93, value - 1, true);
      cpu.cycles++;
    } else if ((opcode & 61440) === 53248) {
      const k = (opcode & 2047) - (opcode & 2048 ? 2048 : 0);
      const retAddr = cpu.pc + 1;
      const sp = cpu.dataView.getUint16(93, true);
      const { pc22Bits } = cpu;
      cpu.data[sp] = 255 & retAddr;
      cpu.data[sp - 1] = retAddr >> 8 & 255;
      if (pc22Bits) {
        cpu.data[sp - 2] = retAddr >> 16 & 255;
      }
      cpu.dataView.setUint16(93, sp - (pc22Bits ? 3 : 2), true);
      cpu.pc += k;
      cpu.cycles += pc22Bits ? 3 : 2;
    } else if (opcode === 38152) {
      const { pc22Bits } = cpu;
      const i = cpu.dataView.getUint16(93, true) + (pc22Bits ? 3 : 2);
      cpu.dataView.setUint16(93, i, true);
      cpu.pc = (cpu.data[i - 1] << 8) + cpu.data[i] - 1;
      if (pc22Bits) {
        cpu.pc |= cpu.data[i - 2] << 16;
      }
      cpu.cycles += pc22Bits ? 4 : 3;
    } else if (opcode === 38168) {
      const { pc22Bits } = cpu;
      const i = cpu.dataView.getUint16(93, true) + (pc22Bits ? 3 : 2);
      cpu.dataView.setUint16(93, i, true);
      cpu.pc = (cpu.data[i - 1] << 8) + cpu.data[i] - 1;
      if (pc22Bits) {
        cpu.pc |= cpu.data[i - 2] << 16;
      }
      cpu.cycles += pc22Bits ? 4 : 3;
      cpu.data[95] |= 128;
    } else if ((opcode & 61440) === 49152) {
      cpu.pc = cpu.pc + ((opcode & 2047) - (opcode & 2048 ? 2048 : 0));
      cpu.cycles++;
    } else if ((opcode & 65039) === 37895) {
      const d = cpu.data[(opcode & 496) >> 4];
      const r = d >>> 1 | (cpu.data[95] & 1) << 7;
      cpu.data[(opcode & 496) >> 4] = r;
      let sreg = cpu.data[95] & 224;
      sreg |= r ? 0 : 2;
      sreg |= 128 & r ? 4 : 0;
      sreg |= 1 & d ? 1 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg & 1 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 64512) === 2048) {
      const val1 = cpu.data[(opcode & 496) >> 4];
      const val2 = cpu.data[opcode & 15 | (opcode & 512) >> 5];
      let sreg = cpu.data[95];
      const R = val1 - val2 - (sreg & 1);
      cpu.data[(opcode & 496) >> 4] = R;
      sreg = sreg & 192 | (!R && sreg >> 1 & 1 ? 2 : 0) | (val2 + (sreg & 1) > val1 ? 1 : 0);
      sreg |= 128 & R ? 4 : 0;
      sreg |= (val1 ^ val2) & (val1 ^ R) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= 1 & (~val1 & val2 | val2 & R | R & ~val1) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 61440) === 16384) {
      const val1 = cpu.data[((opcode & 240) >> 4) + 16];
      const val2 = opcode & 15 | (opcode & 3840) >> 4;
      let sreg = cpu.data[95];
      const R = val1 - val2 - (sreg & 1);
      cpu.data[((opcode & 240) >> 4) + 16] = R;
      sreg = sreg & 192 | (!R && sreg >> 1 & 1 ? 2 : 0) | (val2 + (sreg & 1) > val1 ? 1 : 0);
      sreg |= 128 & R ? 4 : 0;
      sreg |= (val1 ^ val2) & (val1 ^ R) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= 1 & (~val1 & val2 | val2 & R | R & ~val1) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 65280) === 39424) {
      const target = ((opcode & 248) >> 3) + 32;
      const mask = 1 << (opcode & 7);
      cpu.writeData(target, cpu.readData(target) | mask, mask);
      cpu.cycles++;
    } else if ((opcode & 65280) === 39168) {
      const value = cpu.readData(((opcode & 248) >> 3) + 32);
      if (!(value & 1 << (opcode & 7))) {
        const nextOpcode = cpu.progMem[cpu.pc + 1];
        const skipSize = isTwoWordInstruction(nextOpcode) ? 2 : 1;
        cpu.cycles += skipSize;
        cpu.pc += skipSize;
      }
    } else if ((opcode & 65280) === 39680) {
      const value = cpu.readData(((opcode & 248) >> 3) + 32);
      if (value & 1 << (opcode & 7)) {
        const nextOpcode = cpu.progMem[cpu.pc + 1];
        const skipSize = isTwoWordInstruction(nextOpcode) ? 2 : 1;
        cpu.cycles += skipSize;
        cpu.pc += skipSize;
      }
    } else if ((opcode & 65280) === 38656) {
      const i = 2 * ((opcode & 48) >> 4) + 24;
      const a = cpu.dataView.getUint16(i, true);
      const l = opcode & 15 | (opcode & 192) >> 2;
      const R = a - l;
      cpu.dataView.setUint16(i, R, true);
      let sreg = cpu.data[95] & 192;
      sreg |= R ? 0 : 2;
      sreg |= 32768 & R ? 4 : 0;
      sreg |= a & ~R & 32768 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= l > a ? 1 : 0;
      sreg |= 1 & (~a & l | l & R | R & ~a) ? 32 : 0;
      cpu.data[95] = sreg;
      cpu.cycles++;
    } else if ((opcode & 65032) === 64512) {
      if (!(cpu.data[(opcode & 496) >> 4] & 1 << (opcode & 7))) {
        const nextOpcode = cpu.progMem[cpu.pc + 1];
        const skipSize = isTwoWordInstruction(nextOpcode) ? 2 : 1;
        cpu.cycles += skipSize;
        cpu.pc += skipSize;
      }
    } else if ((opcode & 65032) === 65024) {
      if (cpu.data[(opcode & 496) >> 4] & 1 << (opcode & 7)) {
        const nextOpcode = cpu.progMem[cpu.pc + 1];
        const skipSize = isTwoWordInstruction(nextOpcode) ? 2 : 1;
        cpu.cycles += skipSize;
        cpu.pc += skipSize;
      }
    } else if (opcode === 38280) {
    } else if (opcode === 38376) {
    } else if (opcode === 38392) {
    } else if ((opcode & 65039) === 37376) {
      const value = cpu.data[(opcode & 496) >> 4];
      const addr = cpu.progMem[cpu.pc + 1];
      cpu.writeData(addr, value);
      cpu.pc++;
      cpu.cycles++;
    } else if ((opcode & 65039) === 37388) {
      cpu.writeData(cpu.dataView.getUint16(26, true), cpu.data[(opcode & 496) >> 4]);
      cpu.cycles++;
    } else if ((opcode & 65039) === 37389) {
      const x = cpu.dataView.getUint16(26, true);
      cpu.writeData(x, cpu.data[(opcode & 496) >> 4]);
      cpu.dataView.setUint16(26, x + 1, true);
      cpu.cycles++;
    } else if ((opcode & 65039) === 37390) {
      const i = cpu.data[(opcode & 496) >> 4];
      const x = cpu.dataView.getUint16(26, true) - 1;
      cpu.dataView.setUint16(26, x, true);
      cpu.writeData(x, i);
      cpu.cycles++;
    } else if ((opcode & 65039) === 33288) {
      cpu.writeData(cpu.dataView.getUint16(28, true), cpu.data[(opcode & 496) >> 4]);
      cpu.cycles++;
    } else if ((opcode & 65039) === 37385) {
      const i = cpu.data[(opcode & 496) >> 4];
      const y = cpu.dataView.getUint16(28, true);
      cpu.writeData(y, i);
      cpu.dataView.setUint16(28, y + 1, true);
      cpu.cycles++;
    } else if ((opcode & 65039) === 37386) {
      const i = cpu.data[(opcode & 496) >> 4];
      const y = cpu.dataView.getUint16(28, true) - 1;
      cpu.dataView.setUint16(28, y, true);
      cpu.writeData(y, i);
      cpu.cycles++;
    } else if ((opcode & 53768) === 33288 && opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8) {
      cpu.writeData(cpu.dataView.getUint16(28, true) + (opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8), cpu.data[(opcode & 496) >> 4]);
      cpu.cycles++;
    } else if ((opcode & 65039) === 33280) {
      cpu.writeData(cpu.dataView.getUint16(30, true), cpu.data[(opcode & 496) >> 4]);
      cpu.cycles++;
    } else if ((opcode & 65039) === 37377) {
      const z = cpu.dataView.getUint16(30, true);
      cpu.writeData(z, cpu.data[(opcode & 496) >> 4]);
      cpu.dataView.setUint16(30, z + 1, true);
      cpu.cycles++;
    } else if ((opcode & 65039) === 37378) {
      const i = cpu.data[(opcode & 496) >> 4];
      const z = cpu.dataView.getUint16(30, true) - 1;
      cpu.dataView.setUint16(30, z, true);
      cpu.writeData(z, i);
      cpu.cycles++;
    } else if ((opcode & 53768) === 33280 && opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8) {
      cpu.writeData(cpu.dataView.getUint16(30, true) + (opcode & 7 | (opcode & 3072) >> 7 | (opcode & 8192) >> 8), cpu.data[(opcode & 496) >> 4]);
      cpu.cycles++;
    } else if ((opcode & 64512) === 6144) {
      const val1 = cpu.data[(opcode & 496) >> 4];
      const val2 = cpu.data[opcode & 15 | (opcode & 512) >> 5];
      const R = val1 - val2;
      cpu.data[(opcode & 496) >> 4] = R;
      let sreg = cpu.data[95] & 192;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= (val1 ^ val2) & (val1 ^ R) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= val2 > val1 ? 1 : 0;
      sreg |= 1 & (~val1 & val2 | val2 & R | R & ~val1) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 61440) === 20480) {
      const val1 = cpu.data[((opcode & 240) >> 4) + 16];
      const val2 = opcode & 15 | (opcode & 3840) >> 4;
      const R = val1 - val2;
      cpu.data[((opcode & 240) >> 4) + 16] = R;
      let sreg = cpu.data[95] & 192;
      sreg |= R ? 0 : 2;
      sreg |= 128 & R ? 4 : 0;
      sreg |= (val1 ^ val2) & (val1 ^ R) & 128 ? 8 : 0;
      sreg |= sreg >> 2 & 1 ^ sreg >> 3 & 1 ? 16 : 0;
      sreg |= val2 > val1 ? 1 : 0;
      sreg |= 1 & (~val1 & val2 | val2 & R | R & ~val1) ? 32 : 0;
      cpu.data[95] = sreg;
    } else if ((opcode & 65039) === 37890) {
      const d = (opcode & 496) >> 4;
      const i = cpu.data[d];
      cpu.data[d] = (15 & i) << 4 | (240 & i) >>> 4;
    } else if (opcode === 38312) {
      cpu.onWatchdogReset();
    } else if ((opcode & 65039) === 37380) {
      const r = (opcode & 496) >> 4;
      const val1 = cpu.data[r];
      const val2 = cpu.data[cpu.dataView.getUint16(30, true)];
      cpu.data[cpu.dataView.getUint16(30, true)] = val1;
      cpu.data[r] = val2;
    }
    cpu.pc = (cpu.pc + 1) % cpu.progMem.length;
    cpu.cycles++;
  }

  // node_modules/avr8js/dist/esm/peripherals/adc.js
  var ADCReference;
  (function(ADCReference2) {
    ADCReference2[ADCReference2["AVCC"] = 0] = "AVCC";
    ADCReference2[ADCReference2["AREF"] = 1] = "AREF";
    ADCReference2[ADCReference2["Internal1V1"] = 2] = "Internal1V1";
    ADCReference2[ADCReference2["Internal2V56"] = 3] = "Internal2V56";
    ADCReference2[ADCReference2["Reserved"] = 4] = "Reserved";
  })(ADCReference || (ADCReference = {}));
  var ADCMuxInputType;
  (function(ADCMuxInputType2) {
    ADCMuxInputType2[ADCMuxInputType2["SingleEnded"] = 0] = "SingleEnded";
    ADCMuxInputType2[ADCMuxInputType2["Differential"] = 1] = "Differential";
    ADCMuxInputType2[ADCMuxInputType2["Constant"] = 2] = "Constant";
    ADCMuxInputType2[ADCMuxInputType2["Temperature"] = 3] = "Temperature";
  })(ADCMuxInputType || (ADCMuxInputType = {}));
  var atmega328Channels = {
    0: { type: ADCMuxInputType.SingleEnded, channel: 0 },
    1: { type: ADCMuxInputType.SingleEnded, channel: 1 },
    2: { type: ADCMuxInputType.SingleEnded, channel: 2 },
    3: { type: ADCMuxInputType.SingleEnded, channel: 3 },
    4: { type: ADCMuxInputType.SingleEnded, channel: 4 },
    5: { type: ADCMuxInputType.SingleEnded, channel: 5 },
    6: { type: ADCMuxInputType.SingleEnded, channel: 6 },
    7: { type: ADCMuxInputType.SingleEnded, channel: 7 },
    8: { type: ADCMuxInputType.Temperature },
    14: { type: ADCMuxInputType.Constant, voltage: 1.1 },
    15: { type: ADCMuxInputType.Constant, voltage: 0 }
  };
  var fallbackMuxInput = {
    type: ADCMuxInputType.Constant,
    voltage: 0
  };
  var adcConfig = {
    ADMUX: 124,
    ADCSRA: 122,
    ADCSRB: 123,
    ADCL: 120,
    ADCH: 121,
    DIDR0: 126,
    adcInterrupt: 42,
    numChannels: 8,
    muxInputMask: 15,
    muxChannels: atmega328Channels,
    adcReferences: [
      ADCReference.AREF,
      ADCReference.AVCC,
      ADCReference.Reserved,
      ADCReference.Internal1V1
    ]
  };
  var ADPS_MASK = 7;
  var ADIE = 8;
  var ADIF = 16;
  var ADSC = 64;
  var ADEN = 128;
  var MUX_MASK = 31;
  var ADLAR = 32;
  var MUX5 = 8;
  var REFS2 = 8;
  var REFS_MASK = 3;
  var REFS_SHIFT = 6;
  var AVRADC = class {
    constructor(cpu, config) {
      this.cpu = cpu;
      this.config = config;
      this.channelValues = new Array(this.config.numChannels);
      this.avcc = 5;
      this.aref = 5;
      this.onADCRead = (input) => {
        var _a;
        let voltage = 0;
        switch (input.type) {
          case ADCMuxInputType.Constant:
            voltage = input.voltage;
            break;
          case ADCMuxInputType.SingleEnded:
            voltage = (_a = this.channelValues[input.channel]) !== null && _a !== void 0 ? _a : 0;
            break;
          case ADCMuxInputType.Differential:
            voltage = input.gain * ((this.channelValues[input.positiveChannel] || 0) - (this.channelValues[input.negativeChannel] || 0));
            break;
          case ADCMuxInputType.Temperature:
            voltage = 0.378125;
            break;
        }
        const rawValue = voltage / this.referenceVoltage * 1024;
        const result = Math.min(Math.max(Math.floor(rawValue), 0), 1023);
        this.cpu.addClockEvent(() => this.completeADCRead(result), this.sampleCycles);
      };
      this.converting = false;
      this.conversionCycles = 25;
      this.ADC = {
        address: this.config.adcInterrupt,
        flagRegister: this.config.ADCSRA,
        flagMask: ADIF,
        enableRegister: this.config.ADCSRA,
        enableMask: ADIE
      };
      cpu.writeHooks[config.ADCSRA] = (value, oldValue) => {
        var _a;
        if (value & ADEN && !(oldValue && ADEN)) {
          this.conversionCycles = 25;
        }
        cpu.data[config.ADCSRA] = value;
        cpu.updateInterruptEnable(this.ADC, value);
        if (!this.converting && value & ADSC) {
          if (!(value & ADEN)) {
            this.cpu.addClockEvent(() => this.completeADCRead(0), this.sampleCycles);
            return true;
          }
          let channel = this.cpu.data[this.config.ADMUX] & MUX_MASK;
          if (cpu.data[config.ADCSRB] & MUX5) {
            channel |= 32;
          }
          channel &= config.muxInputMask;
          const muxInput = (_a = config.muxChannels[channel]) !== null && _a !== void 0 ? _a : fallbackMuxInput;
          this.converting = true;
          this.onADCRead(muxInput);
          return true;
        }
      };
    }
    completeADCRead(value) {
      const { ADCL, ADCH, ADMUX, ADCSRA } = this.config;
      this.converting = false;
      this.conversionCycles = 13;
      if (this.cpu.data[ADMUX] & ADLAR) {
        this.cpu.data[ADCL] = value << 6 & 255;
        this.cpu.data[ADCH] = value >> 2;
      } else {
        this.cpu.data[ADCL] = value & 255;
        this.cpu.data[ADCH] = value >> 8 & 3;
      }
      this.cpu.data[ADCSRA] &= ~ADSC;
      this.cpu.setInterruptFlag(this.ADC);
    }
    get prescaler() {
      const { ADCSRA } = this.config;
      const adcsra = this.cpu.data[ADCSRA];
      const adps = adcsra & ADPS_MASK;
      switch (adps) {
        case 0:
        case 1:
          return 2;
        case 2:
          return 4;
        case 3:
          return 8;
        case 4:
          return 16;
        case 5:
          return 32;
        case 6:
          return 64;
        case 7:
        default:
          return 128;
      }
    }
    get referenceVoltageType() {
      var _a;
      const { ADMUX, adcReferences } = this.config;
      let refs = this.cpu.data[ADMUX] >> REFS_SHIFT & REFS_MASK;
      if (adcReferences.length > 4 && this.cpu.data[ADMUX] & REFS2) {
        refs |= 4;
      }
      return (_a = adcReferences[refs]) !== null && _a !== void 0 ? _a : ADCReference.Reserved;
    }
    get referenceVoltage() {
      switch (this.referenceVoltageType) {
        case ADCReference.AVCC:
          return this.avcc;
        case ADCReference.AREF:
          return this.aref;
        case ADCReference.Internal1V1:
          return 1.1;
        case ADCReference.Internal2V56:
          return 2.56;
        default:
          return this.avcc;
      }
    }
    get sampleCycles() {
      return this.conversionCycles * this.prescaler;
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/clock.js
  var CLKPCE = 128;
  var clockConfig = {
    CLKPR: 97
  };
  var prescalers = [
    1,
    2,
    4,
    8,
    16,
    32,
    64,
    128,
    256,
    // The following values are "reserved" according to the datasheet, so we measured
    // with a scope to figure them out (on ATmega328p)
    2,
    4,
    8,
    16,
    32,
    64,
    128
  ];
  var AVRClock = class {
    constructor(cpu, baseFreqHz, config = clockConfig) {
      this.cpu = cpu;
      this.baseFreqHz = baseFreqHz;
      this.config = config;
      this.clockEnabledCycles = 0;
      this.prescalerValue = 1;
      this.cyclesDelta = 0;
      this.cpu.writeHooks[this.config.CLKPR] = (clkpr) => {
        if ((!this.clockEnabledCycles || this.clockEnabledCycles < cpu.cycles) && clkpr === CLKPCE) {
          this.clockEnabledCycles = this.cpu.cycles + 4;
        } else if (this.clockEnabledCycles && this.clockEnabledCycles >= cpu.cycles) {
          this.clockEnabledCycles = 0;
          const index = clkpr & 15;
          const oldPrescaler = this.prescalerValue;
          this.prescalerValue = prescalers[index];
          this.cpu.data[this.config.CLKPR] = index;
          if (oldPrescaler !== this.prescalerValue) {
            this.cyclesDelta = (cpu.cycles + this.cyclesDelta) * (oldPrescaler / this.prescalerValue) - cpu.cycles;
          }
        }
        return true;
      };
    }
    get frequency() {
      return this.baseFreqHz / this.prescalerValue;
    }
    get prescaler() {
      return this.prescalerValue;
    }
    get timeNanos() {
      return (this.cpu.cycles + this.cyclesDelta) / this.frequency * 1e9;
    }
    get timeMicros() {
      return (this.cpu.cycles + this.cyclesDelta) / this.frequency * 1e6;
    }
    get timeMillis() {
      return (this.cpu.cycles + this.cyclesDelta) / this.frequency * 1e3;
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/eeprom.js
  var EEPROMMemoryBackend = class {
    constructor(size) {
      this.memory = new Uint8Array(size);
      this.memory.fill(255);
    }
    readMemory(addr) {
      return this.memory[addr];
    }
    writeMemory(addr, value) {
      this.memory[addr] &= value;
    }
    eraseMemory(addr) {
      this.memory[addr] = 255;
    }
  };
  var eepromConfig = {
    eepromReadyInterrupt: 44,
    EECR: 63,
    EEDR: 64,
    EEARL: 65,
    EEARH: 66,
    eraseCycles: 28800,
    writeCycles: 28800
    // 1.8ms at 16MHz
  };
  var EERE = 1 << 0;
  var EEPE = 1 << 1;
  var EEMPE = 1 << 2;
  var EERIE = 1 << 3;
  var EEPM0 = 1 << 4;
  var EEPM1 = 1 << 5;
  var EECR_WRITE_MASK = EEPE | EEMPE | EERIE | EEPM0 | EEPM1;
  var AVREEPROM = class {
    constructor(cpu, backend, config = eepromConfig) {
      this.cpu = cpu;
      this.backend = backend;
      this.config = config;
      this.writeEnabledCycles = 0;
      this.writeCompleteCycles = 0;
      this.EER = {
        address: this.config.eepromReadyInterrupt,
        flagRegister: this.config.EECR,
        flagMask: EEPE,
        enableRegister: this.config.EECR,
        enableMask: EERIE,
        constant: true,
        inverseFlag: true
      };
      this.cpu.writeHooks[this.config.EECR] = (eecr) => {
        const { EEARH, EEARL, EECR, EEDR } = this.config;
        const addr = this.cpu.data[EEARH] << 8 | this.cpu.data[EEARL];
        this.cpu.data[EECR] = this.cpu.data[EECR] & ~EECR_WRITE_MASK | eecr & EECR_WRITE_MASK;
        this.cpu.updateInterruptEnable(this.EER, eecr);
        if (eecr & EERE) {
          this.cpu.clearInterrupt(this.EER);
        }
        if (eecr & EEMPE) {
          const eempeCycles = 4;
          this.writeEnabledCycles = this.cpu.cycles + eempeCycles;
          this.cpu.addClockEvent(() => {
            this.cpu.data[EECR] &= ~EEMPE;
          }, eempeCycles);
        }
        if (eecr & EERE) {
          this.cpu.data[EEDR] = this.backend.readMemory(addr);
          this.cpu.cycles += 4;
          return true;
        }
        if (eecr & EEPE) {
          if (this.cpu.cycles >= this.writeEnabledCycles) {
            this.cpu.data[EECR] &= ~EEPE;
            return true;
          }
          if (this.cpu.cycles < this.writeCompleteCycles) {
            return true;
          }
          const eedr = this.cpu.data[EEDR];
          this.writeCompleteCycles = this.cpu.cycles;
          if (!(eecr & EEPM1)) {
            this.backend.eraseMemory(addr);
            this.writeCompleteCycles += this.config.eraseCycles;
          }
          if (!(eecr & EEPM0)) {
            this.backend.writeMemory(addr, eedr);
            this.writeCompleteCycles += this.config.writeCycles;
          }
          this.cpu.data[EECR] |= EEPE;
          this.cpu.addClockEvent(() => {
            this.cpu.setInterruptFlag(this.EER);
          }, this.writeCompleteCycles - this.cpu.cycles);
          this.cpu.cycles += 2;
        }
        return true;
      };
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/gpio.js
  var INT0 = {
    EICR: 105,
    EIMSK: 61,
    EIFR: 60,
    index: 0,
    iscOffset: 0,
    interrupt: 2
  };
  var INT1 = {
    EICR: 105,
    EIMSK: 61,
    EIFR: 60,
    index: 1,
    iscOffset: 2,
    interrupt: 4
  };
  var PCINT0 = {
    PCIE: 0,
    PCICR: 104,
    PCIFR: 59,
    PCMSK: 107,
    pinChangeInterrupt: 6,
    mask: 255,
    offset: 0
  };
  var PCINT1 = {
    PCIE: 1,
    PCICR: 104,
    PCIFR: 59,
    PCMSK: 108,
    pinChangeInterrupt: 8,
    mask: 255,
    offset: 0
  };
  var PCINT2 = {
    PCIE: 2,
    PCICR: 104,
    PCIFR: 59,
    PCMSK: 109,
    pinChangeInterrupt: 10,
    mask: 255,
    offset: 0
  };
  var portAConfig = {
    PIN: 32,
    DDR: 33,
    PORT: 34,
    externalInterrupts: []
  };
  var portBConfig = {
    PIN: 35,
    DDR: 36,
    PORT: 37,
    // Interrupt settings
    pinChange: PCINT0,
    externalInterrupts: []
  };
  var portCConfig = {
    PIN: 38,
    DDR: 39,
    PORT: 40,
    // Interrupt settings
    pinChange: PCINT1,
    externalInterrupts: []
  };
  var portDConfig = {
    PIN: 41,
    DDR: 42,
    PORT: 43,
    // Interrupt settings
    pinChange: PCINT2,
    externalInterrupts: [null, null, INT0, INT1]
  };
  var portEConfig = {
    PIN: 44,
    DDR: 45,
    PORT: 46,
    externalInterrupts: []
  };
  var portFConfig = {
    PIN: 47,
    DDR: 48,
    PORT: 49,
    externalInterrupts: []
  };
  var portGConfig = {
    PIN: 50,
    DDR: 51,
    PORT: 52,
    externalInterrupts: []
  };
  var portHConfig = {
    PIN: 256,
    DDR: 257,
    PORT: 258,
    externalInterrupts: []
  };
  var portJConfig = {
    PIN: 259,
    DDR: 260,
    PORT: 261,
    externalInterrupts: []
  };
  var portKConfig = {
    PIN: 262,
    DDR: 263,
    PORT: 264,
    externalInterrupts: []
  };
  var portLConfig = {
    PIN: 265,
    DDR: 266,
    PORT: 267,
    externalInterrupts: []
  };
  var PinState;
  (function(PinState2) {
    PinState2[PinState2["Low"] = 0] = "Low";
    PinState2[PinState2["High"] = 1] = "High";
    PinState2[PinState2["Input"] = 2] = "Input";
    PinState2[PinState2["InputPullUp"] = 3] = "InputPullUp";
  })(PinState || (PinState = {}));
  var PinOverrideMode;
  (function(PinOverrideMode2) {
    PinOverrideMode2[PinOverrideMode2["None"] = 0] = "None";
    PinOverrideMode2[PinOverrideMode2["Enable"] = 1] = "Enable";
    PinOverrideMode2[PinOverrideMode2["Set"] = 2] = "Set";
    PinOverrideMode2[PinOverrideMode2["Clear"] = 3] = "Clear";
    PinOverrideMode2[PinOverrideMode2["Toggle"] = 4] = "Toggle";
  })(PinOverrideMode || (PinOverrideMode = {}));
  var InterruptMode;
  (function(InterruptMode2) {
    InterruptMode2[InterruptMode2["LowLevel"] = 0] = "LowLevel";
    InterruptMode2[InterruptMode2["Change"] = 1] = "Change";
    InterruptMode2[InterruptMode2["FallingEdge"] = 2] = "FallingEdge";
    InterruptMode2[InterruptMode2["RisingEdge"] = 3] = "RisingEdge";
  })(InterruptMode || (InterruptMode = {}));
  var AVRIOPort = class {
    constructor(cpu, portConfig) {
      var _a, _b, _c, _d;
      this.cpu = cpu;
      this.portConfig = portConfig;
      this.externalClockListeners = [];
      this.listeners = [];
      this.pinValue = 0;
      this.overrideMask = 255;
      this.overrideValue = 0;
      this.lastValue = 0;
      this.lastDdr = 0;
      this.lastPin = 0;
      this.openCollector = 0;
      cpu.gpioPorts.add(this);
      cpu.gpioByPort[portConfig.PORT] = this;
      cpu.writeHooks[portConfig.DDR] = (value) => {
        const portValue = cpu.data[portConfig.PORT];
        cpu.data[portConfig.DDR] = value;
        this.writeGpio(portValue, value);
        this.updatePinRegister(value);
        return true;
      };
      cpu.writeHooks[portConfig.PORT] = (value) => {
        const ddrMask = cpu.data[portConfig.DDR];
        cpu.data[portConfig.PORT] = value;
        this.writeGpio(value, ddrMask);
        this.updatePinRegister(ddrMask);
        return true;
      };
      cpu.writeHooks[portConfig.PIN] = (value, oldValue, addr, mask) => {
        const oldPortValue = cpu.data[portConfig.PORT];
        const ddrMask = cpu.data[portConfig.DDR];
        const portValue = oldPortValue ^ value & mask;
        cpu.data[portConfig.PORT] = portValue;
        this.writeGpio(portValue, ddrMask);
        this.updatePinRegister(ddrMask);
        return true;
      };
      const { externalInterrupts } = portConfig;
      this.externalInts = externalInterrupts.map((externalConfig) => externalConfig ? {
        address: externalConfig.interrupt,
        flagRegister: externalConfig.EIFR,
        flagMask: 1 << externalConfig.index,
        enableRegister: externalConfig.EIMSK,
        enableMask: 1 << externalConfig.index
      } : null);
      const EICR = new Set(externalInterrupts.map((item) => item === null || item === void 0 ? void 0 : item.EICR));
      for (const EICRx of EICR) {
        this.attachInterruptHook(EICRx || 0);
      }
      const EIMSK = (_b = (_a = externalInterrupts.find((item) => item && item.EIMSK)) === null || _a === void 0 ? void 0 : _a.EIMSK) !== null && _b !== void 0 ? _b : 0;
      this.attachInterruptHook(EIMSK, "mask");
      const EIFR = (_d = (_c = externalInterrupts.find((item) => item && item.EIFR)) === null || _c === void 0 ? void 0 : _c.EIFR) !== null && _d !== void 0 ? _d : 0;
      this.attachInterruptHook(EIFR, "flag");
      const { pinChange } = portConfig;
      this.PCINT = pinChange ? {
        address: pinChange.pinChangeInterrupt,
        flagRegister: pinChange.PCIFR,
        flagMask: 1 << pinChange.PCIE,
        enableRegister: pinChange.PCICR,
        enableMask: 1 << pinChange.PCIE
      } : null;
      if (pinChange) {
        const { PCIFR, PCMSK } = pinChange;
        cpu.writeHooks[PCIFR] = (value) => {
          for (const gpio of this.cpu.gpioPorts) {
            const { PCINT } = gpio;
            if (PCINT) {
              cpu.clearInterruptByFlag(PCINT, value);
            }
          }
          return true;
        };
        cpu.writeHooks[PCMSK] = (value) => {
          cpu.data[PCMSK] = value;
          for (const gpio of this.cpu.gpioPorts) {
            const { PCINT } = gpio;
            if (PCINT) {
              cpu.updateInterruptEnable(PCINT, value);
            }
          }
          return true;
        };
      }
    }
    addListener(listener) {
      this.listeners.push(listener);
    }
    removeListener(listener) {
      this.listeners = this.listeners.filter((l) => l !== listener);
    }
    /**
     * Get the state of a given GPIO pin
     *
     * @param index Pin index to return from 0 to 7
     * @returns PinState.Low or PinState.High if the pin is set to output, PinState.Input if the pin is set
     *   to input, and PinState.InputPullUp if the pin is set to input and the internal pull-up resistor has
     *   been enabled.
     */
    pinState(index) {
      const ddr = this.cpu.data[this.portConfig.DDR];
      const port = this.cpu.data[this.portConfig.PORT];
      const bitMask = 1 << index;
      const openState = port & bitMask ? PinState.InputPullUp : PinState.Input;
      const highValue = this.openCollector & bitMask ? openState : PinState.High;
      if (ddr & bitMask) {
        return this.lastValue & bitMask ? highValue : PinState.Low;
      } else {
        return openState;
      }
    }
    /**
     * Sets the input value for the given pin. This is the value that
     * will be returned when reading from the PIN register.
     */
    setPin(index, value) {
      const bitMask = 1 << index;
      this.pinValue &= ~bitMask;
      if (value) {
        this.pinValue |= bitMask;
      }
      this.updatePinRegister(this.cpu.data[this.portConfig.DDR]);
    }
    /**
     * Internal method - do not call this directly!
     * Used by the timer compare output units to override GPIO pins.
     */
    timerOverridePin(pin, mode) {
      const { cpu, portConfig } = this;
      const pinMask = 1 << pin;
      if (mode === PinOverrideMode.None) {
        this.overrideMask |= pinMask;
        this.overrideValue &= ~pinMask;
      } else {
        this.overrideMask &= ~pinMask;
        switch (mode) {
          case PinOverrideMode.Enable:
            this.overrideValue &= ~pinMask;
            this.overrideValue |= cpu.data[portConfig.PORT] & pinMask;
            break;
          case PinOverrideMode.Set:
            this.overrideValue |= pinMask;
            break;
          case PinOverrideMode.Clear:
            this.overrideValue &= ~pinMask;
            break;
          case PinOverrideMode.Toggle:
            this.overrideValue ^= pinMask;
            break;
        }
      }
      const ddrMask = cpu.data[portConfig.DDR];
      this.writeGpio(cpu.data[portConfig.PORT], ddrMask);
      this.updatePinRegister(ddrMask);
    }
    updatePinRegister(ddr) {
      var _a, _b;
      const newPin = this.pinValue & ~ddr | this.lastValue & ddr;
      this.cpu.data[this.portConfig.PIN] = newPin;
      if (this.lastPin !== newPin) {
        for (let index = 0; index < 8; index++) {
          if ((newPin & 1 << index) !== (this.lastPin & 1 << index)) {
            const value = !!(newPin & 1 << index);
            this.toggleInterrupt(index, value);
            (_b = (_a = this.externalClockListeners)[index]) === null || _b === void 0 ? void 0 : _b.call(_a, value);
          }
        }
        this.lastPin = newPin;
      }
    }
    toggleInterrupt(pin, risingEdge) {
      const { cpu, portConfig, externalInts, PCINT } = this;
      const { externalInterrupts, pinChange } = portConfig;
      const externalConfig = externalInterrupts[pin];
      const external = externalInts[pin];
      if (external && externalConfig) {
        const { EIMSK, index, EICR, iscOffset } = externalConfig;
        if (cpu.data[EIMSK] & 1 << index) {
          const configuration = cpu.data[EICR] >> iscOffset & 3;
          let generateInterrupt = false;
          external.constant = false;
          switch (configuration) {
            case InterruptMode.LowLevel:
              generateInterrupt = !risingEdge;
              external.constant = true;
              break;
            case InterruptMode.Change:
              generateInterrupt = true;
              break;
            case InterruptMode.FallingEdge:
              generateInterrupt = !risingEdge;
              break;
            case InterruptMode.RisingEdge:
              generateInterrupt = risingEdge;
              break;
          }
          if (generateInterrupt) {
            cpu.setInterruptFlag(external);
          } else if (external.constant) {
            cpu.clearInterrupt(external, true);
          }
        }
      }
      if (pinChange && PCINT && pinChange.mask & 1 << pin) {
        const { PCMSK } = pinChange;
        if (cpu.data[PCMSK] & 1 << pin + pinChange.offset) {
          cpu.setInterruptFlag(PCINT);
        }
      }
    }
    attachInterruptHook(register, registerType = "other") {
      if (!register) {
        return;
      }
      const { cpu } = this;
      cpu.writeHooks[register] = (value) => {
        if (registerType !== "flag") {
          cpu.data[register] = value;
        }
        for (const gpio of cpu.gpioPorts) {
          for (const external of gpio.externalInts) {
            if (external && registerType === "mask") {
              cpu.updateInterruptEnable(external, value);
            }
            if (external && !external.constant && registerType === "flag") {
              cpu.clearInterruptByFlag(external, value);
            }
          }
          gpio.checkExternalInterrupts();
        }
        return true;
      };
    }
    checkExternalInterrupts() {
      const { cpu } = this;
      const { externalInterrupts } = this.portConfig;
      for (let pin = 0; pin < 8; pin++) {
        const external = externalInterrupts[pin];
        if (!external) {
          continue;
        }
        const pinValue = !!(this.lastPin & 1 << pin);
        const { EIFR, EIMSK, index, EICR, iscOffset, interrupt } = external;
        if (!(cpu.data[EIMSK] & 1 << index) || pinValue) {
          continue;
        }
        const configuration = cpu.data[EICR] >> iscOffset & 3;
        if (configuration === InterruptMode.LowLevel) {
          cpu.queueInterrupt({
            address: interrupt,
            flagRegister: EIFR,
            flagMask: 1 << index,
            enableRegister: EIMSK,
            enableMask: 1 << index,
            constant: true
          });
        }
      }
    }
    writeGpio(value, ddr) {
      const newValue = (value & this.overrideMask | this.overrideValue) & ddr | value & ~ddr;
      const prevValue = this.lastValue;
      if (newValue !== prevValue || ddr !== this.lastDdr) {
        this.lastValue = newValue;
        this.lastDdr = ddr;
        for (const listener of this.listeners) {
          listener(newValue, prevValue);
        }
      }
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/spi.js
  var SPCR_SPIE = 128;
  var SPCR_SPE = 64;
  var SPCR_DORD = 32;
  var SPCR_MSTR = 16;
  var SPCR_CPOL = 8;
  var SPCR_CPHA = 4;
  var SPCR_SPR1 = 2;
  var SPCR_SPR0 = 1;
  var SPSR_SPR_MASK = SPCR_SPR1 | SPCR_SPR0;
  var SPSR_SPIF = 128;
  var SPSR_WCOL = 64;
  var SPSR_SPI2X = 1;
  var spiConfig = {
    spiInterrupt: 34,
    SPCR: 76,
    SPSR: 77,
    SPDR: 78
  };
  var bitsPerByte = 8;
  var AVRSPI = class {
    constructor(cpu, config, freqHz) {
      this.cpu = cpu;
      this.config = config;
      this.freqHz = freqHz;
      this.onTransfer = () => 0;
      this.onByte = (value) => {
        const valueIn = this.onTransfer(value);
        this.cpu.addClockEvent(() => this.completeTransfer(valueIn), this.transferCycles);
      };
      this.transmissionActive = false;
      this.SPI = {
        address: this.config.spiInterrupt,
        flagRegister: this.config.SPSR,
        flagMask: SPSR_SPIF,
        enableRegister: this.config.SPCR,
        enableMask: SPCR_SPIE
      };
      const { SPCR, SPSR, SPDR } = config;
      cpu.writeHooks[SPDR] = (value) => {
        if (!(cpu.data[SPCR] & SPCR_SPE)) {
          return;
        }
        if (this.transmissionActive) {
          cpu.data[SPSR] |= SPSR_WCOL;
          return true;
        }
        cpu.data[SPSR] &= ~SPSR_WCOL;
        this.cpu.clearInterrupt(this.SPI);
        this.transmissionActive = true;
        this.onByte(value);
        return true;
      };
      cpu.writeHooks[SPCR] = (value) => {
        this.cpu.updateInterruptEnable(this.SPI, value);
      };
      cpu.writeHooks[SPSR] = (value) => {
        this.cpu.data[SPSR] = value;
        this.cpu.clearInterruptByFlag(this.SPI, value);
      };
    }
    reset() {
      this.transmissionActive = false;
    }
    /**
     * Completes an SPI transaction. Call this method only from the `onByte` callback.
     *
     * @param receivedByte Byte read from the SPI MISO line.
     */
    completeTransfer(receivedByte) {
      const { SPDR } = this.config;
      this.cpu.data[SPDR] = receivedByte;
      this.cpu.setInterruptFlag(this.SPI);
      this.transmissionActive = false;
    }
    get isMaster() {
      return this.cpu.data[this.config.SPCR] & SPCR_MSTR ? true : false;
    }
    get dataOrder() {
      return this.cpu.data[this.config.SPCR] & SPCR_DORD ? "lsbFirst" : "msbFirst";
    }
    get spiMode() {
      const CPHA = this.cpu.data[this.config.SPCR] & SPCR_CPHA;
      const CPOL = this.cpu.data[this.config.SPCR] & SPCR_CPOL;
      return (CPHA ? 2 : 0) | (CPOL ? 1 : 0);
    }
    /**
     * The clock divider is only relevant for Master mode
     */
    get clockDivider() {
      const base = this.cpu.data[this.config.SPSR] & SPSR_SPI2X ? 2 : 4;
      switch (this.cpu.data[this.config.SPCR] & SPSR_SPR_MASK) {
        case 0:
          return base;
        case 1:
          return base * 4;
        case 2:
          return base * 16;
        case 3:
          return base * 32;
      }
      throw new Error("Invalid divider value!");
    }
    /** Number of cycles to complete a single byte SPI transaction */
    get transferCycles() {
      return this.clockDivider * bitsPerByte;
    }
    /**
     * The SPI freqeuncy is only relevant to Master mode.
     * In slave mode, the frequency can be as high as F(osc) / 4.
     */
    get spiFrequency() {
      return this.freqHz / this.clockDivider;
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/timer.js
  var timer01Dividers = {
    0: 0,
    1: 1,
    2: 8,
    3: 64,
    4: 256,
    5: 1024,
    6: 0,
    7: 0
    // Ditto
  };
  var ExternalClockMode;
  (function(ExternalClockMode2) {
    ExternalClockMode2[ExternalClockMode2["FallingEdge"] = 6] = "FallingEdge";
    ExternalClockMode2[ExternalClockMode2["RisingEdge"] = 7] = "RisingEdge";
  })(ExternalClockMode || (ExternalClockMode = {}));
  var defaultTimerBits = {
    // TIFR bits
    TOV: 1,
    OCFA: 2,
    OCFB: 4,
    OCFC: 0,
    // TIMSK bits
    TOIE: 1,
    OCIEA: 2,
    OCIEB: 4,
    OCIEC: 0
    // Unused
  };
  var timer0Config = Object.assign({ bits: 8, captureInterrupt: 0, compAInterrupt: 28, compBInterrupt: 30, compCInterrupt: 0, ovfInterrupt: 32, TIFR: 53, OCRA: 71, OCRB: 72, OCRC: 0, ICR: 0, TCNT: 70, TCCRA: 68, TCCRB: 69, TCCRC: 0, TIMSK: 110, dividers: timer01Dividers, compPortA: portDConfig.PORT, compPinA: 6, compPortB: portDConfig.PORT, compPinB: 5, compPortC: 0, compPinC: 0, externalClockPort: portDConfig.PORT, externalClockPin: 4 }, defaultTimerBits);
  var timer1Config = Object.assign({ bits: 16, captureInterrupt: 20, compAInterrupt: 22, compBInterrupt: 24, compCInterrupt: 0, ovfInterrupt: 26, TIFR: 54, OCRA: 136, OCRB: 138, OCRC: 0, ICR: 134, TCNT: 132, TCCRA: 128, TCCRB: 129, TCCRC: 130, TIMSK: 111, dividers: timer01Dividers, compPortA: portBConfig.PORT, compPinA: 1, compPortB: portBConfig.PORT, compPinB: 2, compPortC: 0, compPinC: 0, externalClockPort: portDConfig.PORT, externalClockPin: 5 }, defaultTimerBits);
  var timer2Config = Object.assign({ bits: 8, captureInterrupt: 0, compAInterrupt: 14, compBInterrupt: 16, compCInterrupt: 0, ovfInterrupt: 18, TIFR: 55, OCRA: 179, OCRB: 180, OCRC: 0, ICR: 0, TCNT: 178, TCCRA: 176, TCCRB: 177, TCCRC: 0, TIMSK: 112, dividers: {
    0: 0,
    1: 1,
    2: 8,
    3: 32,
    4: 64,
    5: 128,
    6: 256,
    7: 1024
  }, compPortA: portBConfig.PORT, compPinA: 3, compPortB: portDConfig.PORT, compPinB: 3, compPortC: 0, compPinC: 0, externalClockPort: 0, externalClockPin: 0 }, defaultTimerBits);
  var TimerMode;
  (function(TimerMode2) {
    TimerMode2[TimerMode2["Normal"] = 0] = "Normal";
    TimerMode2[TimerMode2["PWMPhaseCorrect"] = 1] = "PWMPhaseCorrect";
    TimerMode2[TimerMode2["CTC"] = 2] = "CTC";
    TimerMode2[TimerMode2["FastPWM"] = 3] = "FastPWM";
    TimerMode2[TimerMode2["PWMPhaseFrequencyCorrect"] = 4] = "PWMPhaseFrequencyCorrect";
    TimerMode2[TimerMode2["Reserved"] = 5] = "Reserved";
  })(TimerMode || (TimerMode = {}));
  var TOVUpdateMode;
  (function(TOVUpdateMode2) {
    TOVUpdateMode2[TOVUpdateMode2["Max"] = 0] = "Max";
    TOVUpdateMode2[TOVUpdateMode2["Top"] = 1] = "Top";
    TOVUpdateMode2[TOVUpdateMode2["Bottom"] = 2] = "Bottom";
  })(TOVUpdateMode || (TOVUpdateMode = {}));
  var OCRUpdateMode;
  (function(OCRUpdateMode2) {
    OCRUpdateMode2[OCRUpdateMode2["Immediate"] = 0] = "Immediate";
    OCRUpdateMode2[OCRUpdateMode2["Top"] = 1] = "Top";
    OCRUpdateMode2[OCRUpdateMode2["Bottom"] = 2] = "Bottom";
  })(OCRUpdateMode || (OCRUpdateMode = {}));
  var TopOCRA = 1;
  var TopICR = 2;
  var OCToggle = 1;
  var { Normal, PWMPhaseCorrect, CTC, FastPWM, Reserved, PWMPhaseFrequencyCorrect } = TimerMode;
  var wgmModes8Bit = [
    /*0*/
    [Normal, 255, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*1*/
    [PWMPhaseCorrect, 255, OCRUpdateMode.Top, TOVUpdateMode.Bottom, 0],
    /*2*/
    [CTC, TopOCRA, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*3*/
    [FastPWM, 255, OCRUpdateMode.Bottom, TOVUpdateMode.Max, 0],
    /*4*/
    [Reserved, 255, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*5*/
    [PWMPhaseCorrect, TopOCRA, OCRUpdateMode.Top, TOVUpdateMode.Bottom, OCToggle],
    /*6*/
    [Reserved, 255, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*7*/
    [FastPWM, TopOCRA, OCRUpdateMode.Bottom, TOVUpdateMode.Top, OCToggle]
  ];
  var wgmModes16Bit = [
    /*0 */
    [Normal, 65535, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*1 */
    [PWMPhaseCorrect, 255, OCRUpdateMode.Top, TOVUpdateMode.Bottom, 0],
    /*2 */
    [PWMPhaseCorrect, 511, OCRUpdateMode.Top, TOVUpdateMode.Bottom, 0],
    /*3 */
    [PWMPhaseCorrect, 1023, OCRUpdateMode.Top, TOVUpdateMode.Bottom, 0],
    /*4 */
    [CTC, TopOCRA, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*5 */
    [FastPWM, 255, OCRUpdateMode.Bottom, TOVUpdateMode.Top, 0],
    /*6 */
    [FastPWM, 511, OCRUpdateMode.Bottom, TOVUpdateMode.Top, 0],
    /*7 */
    [FastPWM, 1023, OCRUpdateMode.Bottom, TOVUpdateMode.Top, 0],
    /*8 */
    [PWMPhaseFrequencyCorrect, TopICR, OCRUpdateMode.Bottom, TOVUpdateMode.Bottom, 0],
    /*9 */
    [PWMPhaseFrequencyCorrect, TopOCRA, OCRUpdateMode.Bottom, TOVUpdateMode.Bottom, OCToggle],
    /*10*/
    [PWMPhaseCorrect, TopICR, OCRUpdateMode.Top, TOVUpdateMode.Bottom, 0],
    /*11*/
    [PWMPhaseCorrect, TopOCRA, OCRUpdateMode.Top, TOVUpdateMode.Bottom, OCToggle],
    /*12*/
    [CTC, TopICR, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*13*/
    [Reserved, 65535, OCRUpdateMode.Immediate, TOVUpdateMode.Max, 0],
    /*14*/
    [FastPWM, TopICR, OCRUpdateMode.Bottom, TOVUpdateMode.Top, OCToggle],
    /*15*/
    [FastPWM, TopOCRA, OCRUpdateMode.Bottom, TOVUpdateMode.Top, OCToggle]
  ];
  function compToOverride(comp) {
    switch (comp) {
      case 1:
        return PinOverrideMode.Toggle;
      case 2:
        return PinOverrideMode.Clear;
      case 3:
        return PinOverrideMode.Set;
      default:
        return PinOverrideMode.Enable;
    }
  }
  var FOCA = 1 << 7;
  var FOCB = 1 << 6;
  var FOCC = 1 << 5;
  var AVRTimer = class {
    constructor(cpu, config) {
      this.cpu = cpu;
      this.config = config;
      this.MAX = this.config.bits === 16 ? 65535 : 255;
      this.lastCycle = 0;
      this.ocrA = 0;
      this.nextOcrA = 0;
      this.ocrB = 0;
      this.nextOcrB = 0;
      this.hasOCRC = this.config.OCRC > 0;
      this.ocrC = 0;
      this.nextOcrC = 0;
      this.ocrUpdateMode = OCRUpdateMode.Immediate;
      this.tovUpdateMode = TOVUpdateMode.Max;
      this.icr = 0;
      this.tcnt = 0;
      this.tcntNext = 0;
      this.tcntUpdated = false;
      this.updateDivider = false;
      this.countingUp = true;
      this.divider = 0;
      this.externalClockRisingEdge = false;
      this.highByteTemp = 0;
      this.OVF = {
        address: this.config.ovfInterrupt,
        flagRegister: this.config.TIFR,
        flagMask: this.config.TOV,
        enableRegister: this.config.TIMSK,
        enableMask: this.config.TOIE
      };
      this.OCFA = {
        address: this.config.compAInterrupt,
        flagRegister: this.config.TIFR,
        flagMask: this.config.OCFA,
        enableRegister: this.config.TIMSK,
        enableMask: this.config.OCIEA
      };
      this.OCFB = {
        address: this.config.compBInterrupt,
        flagRegister: this.config.TIFR,
        flagMask: this.config.OCFB,
        enableRegister: this.config.TIMSK,
        enableMask: this.config.OCIEB
      };
      this.OCFC = {
        address: this.config.compCInterrupt,
        flagRegister: this.config.TIFR,
        flagMask: this.config.OCFC,
        enableRegister: this.config.TIMSK,
        enableMask: this.config.OCIEC
      };
      this.count = (reschedule = true, external = false) => {
        const { divider, lastCycle, cpu: cpu2 } = this;
        const { cycles } = cpu2;
        const delta = cycles - lastCycle;
        if (divider && delta >= divider || external) {
          const counterDelta = external ? 1 : Math.floor(delta / divider);
          this.lastCycle += counterDelta * divider;
          const val = this.tcnt;
          const { timerMode, TOP } = this;
          const phasePwm = timerMode === PWMPhaseCorrect || timerMode === PWMPhaseFrequencyCorrect;
          const newVal = phasePwm ? this.phasePwmCount(val, counterDelta) : (val + counterDelta) % (TOP + 1);
          const overflow = val + counterDelta > TOP;
          if (!this.tcntUpdated) {
            this.tcnt = newVal;
            if (!phasePwm) {
              this.timerUpdated(newVal, val);
            }
          }
          if (!phasePwm) {
            if (timerMode === FastPWM && overflow) {
              const { compA, compB } = this;
              if (compA) {
                this.updateCompPin(compA, "A", true);
              }
              if (compB) {
                this.updateCompPin(compB, "B", true);
              }
            }
            if (this.ocrUpdateMode == OCRUpdateMode.Bottom && overflow) {
              this.ocrA = this.nextOcrA;
              this.ocrB = this.nextOcrB;
              this.ocrC = this.nextOcrC;
            }
            if (overflow && (this.tovUpdateMode == TOVUpdateMode.Top || TOP === this.MAX)) {
              cpu2.setInterruptFlag(this.OVF);
            }
          }
        }
        if (this.tcntUpdated) {
          this.tcnt = this.tcntNext;
          this.tcntUpdated = false;
          if (this.tcnt === 0 && this.ocrUpdateMode === OCRUpdateMode.Bottom || this.tcnt === this.TOP && this.ocrUpdateMode === OCRUpdateMode.Top) {
            this.ocrA = this.nextOcrA;
            this.ocrB = this.nextOcrB;
            this.ocrC = this.nextOcrC;
          }
        }
        if (this.updateDivider) {
          const { CS } = this;
          const { externalClockPin } = this.config;
          const newDivider = this.config.dividers[CS];
          this.lastCycle = newDivider ? this.cpu.cycles : 0;
          this.updateDivider = false;
          this.divider = newDivider;
          if (this.config.externalClockPort && !this.externalClockPort) {
            this.externalClockPort = this.cpu.gpioByPort[this.config.externalClockPort];
          }
          if (this.externalClockPort) {
            this.externalClockPort.externalClockListeners[externalClockPin] = null;
          }
          if (newDivider) {
            cpu2.addClockEvent(this.count, this.lastCycle + newDivider - cpu2.cycles);
          } else if (this.externalClockPort && (CS === ExternalClockMode.FallingEdge || CS === ExternalClockMode.RisingEdge)) {
            this.externalClockPort.externalClockListeners[externalClockPin] = this.externalClockCallback;
            this.externalClockRisingEdge = CS === ExternalClockMode.RisingEdge;
          }
          return;
        }
        if (reschedule && divider) {
          cpu2.addClockEvent(this.count, this.lastCycle + divider - cpu2.cycles);
        }
      };
      this.externalClockCallback = (value) => {
        if (value === this.externalClockRisingEdge) {
          this.count(false, true);
        }
      };
      this.updateWGMConfig();
      this.cpu.readHooks[config.TCNT] = (addr) => {
        this.count(false);
        if (this.config.bits === 16) {
          this.cpu.data[addr + 1] = this.tcnt >> 8;
        }
        return this.cpu.data[addr] = this.tcnt & 255;
      };
      this.cpu.writeHooks[config.TCNT] = (value) => {
        this.tcntNext = this.highByteTemp << 8 | value;
        this.countingUp = true;
        this.tcntUpdated = true;
        this.cpu.updateClockEvent(this.count, 0);
        if (this.divider) {
          this.timerUpdated(this.tcntNext, this.tcntNext);
        }
      };
      this.cpu.writeHooks[config.OCRA] = (value) => {
        this.nextOcrA = this.highByteTemp << 8 | value;
        if (this.ocrUpdateMode === OCRUpdateMode.Immediate) {
          this.ocrA = this.nextOcrA;
        }
      };
      this.cpu.writeHooks[config.OCRB] = (value) => {
        this.nextOcrB = this.highByteTemp << 8 | value;
        if (this.ocrUpdateMode === OCRUpdateMode.Immediate) {
          this.ocrB = this.nextOcrB;
        }
      };
      if (this.hasOCRC) {
        this.cpu.writeHooks[config.OCRC] = (value) => {
          this.nextOcrC = this.highByteTemp << 8 | value;
          if (this.ocrUpdateMode === OCRUpdateMode.Immediate) {
            this.ocrC = this.nextOcrC;
          }
        };
      }
      if (this.config.bits === 16) {
        this.cpu.writeHooks[config.ICR] = (value) => {
          this.icr = this.highByteTemp << 8 | value;
        };
        const updateTempRegister = (value) => {
          this.highByteTemp = value;
        };
        const updateOCRHighRegister = (value, old, addr) => {
          this.highByteTemp = value & this.ocrMask >> 8;
          cpu.data[addr] = this.highByteTemp;
          return true;
        };
        this.cpu.writeHooks[config.TCNT + 1] = updateTempRegister;
        this.cpu.writeHooks[config.OCRA + 1] = updateOCRHighRegister;
        this.cpu.writeHooks[config.OCRB + 1] = updateOCRHighRegister;
        if (this.hasOCRC) {
          this.cpu.writeHooks[config.OCRC + 1] = updateOCRHighRegister;
        }
        this.cpu.writeHooks[config.ICR + 1] = updateTempRegister;
      }
      cpu.writeHooks[config.TCCRA] = (value) => {
        this.cpu.data[config.TCCRA] = value;
        this.updateWGMConfig();
        return true;
      };
      cpu.writeHooks[config.TCCRB] = (value) => {
        if (!config.TCCRC) {
          this.checkForceCompare(value);
          value &= ~(FOCA | FOCB);
        }
        this.cpu.data[config.TCCRB] = value;
        this.updateDivider = true;
        this.cpu.clearClockEvent(this.count);
        this.cpu.addClockEvent(this.count, 0);
        this.updateWGMConfig();
        return true;
      };
      if (config.TCCRC) {
        cpu.writeHooks[config.TCCRC] = (value) => {
          this.checkForceCompare(value);
        };
      }
      cpu.writeHooks[config.TIFR] = (value) => {
        this.cpu.data[config.TIFR] = value;
        this.cpu.clearInterruptByFlag(this.OVF, value);
        this.cpu.clearInterruptByFlag(this.OCFA, value);
        this.cpu.clearInterruptByFlag(this.OCFB, value);
        return true;
      };
      cpu.writeHooks[config.TIMSK] = (value) => {
        this.cpu.updateInterruptEnable(this.OVF, value);
        this.cpu.updateInterruptEnable(this.OCFA, value);
        this.cpu.updateInterruptEnable(this.OCFB, value);
      };
    }
    reset() {
      this.divider = 0;
      this.lastCycle = 0;
      this.ocrA = 0;
      this.nextOcrA = 0;
      this.ocrB = 0;
      this.nextOcrB = 0;
      this.ocrC = 0;
      this.nextOcrC = 0;
      this.icr = 0;
      this.tcnt = 0;
      this.tcntNext = 0;
      this.tcntUpdated = false;
      this.countingUp = false;
      this.updateDivider = true;
    }
    get TCCRA() {
      return this.cpu.data[this.config.TCCRA];
    }
    get TCCRB() {
      return this.cpu.data[this.config.TCCRB];
    }
    get TIMSK() {
      return this.cpu.data[this.config.TIMSK];
    }
    get CS() {
      return this.TCCRB & 7;
    }
    get WGM() {
      const mask = this.config.bits === 16 ? 24 : 8;
      return (this.TCCRB & mask) >> 1 | this.TCCRA & 3;
    }
    get TOP() {
      switch (this.topValue) {
        case TopOCRA:
          return this.ocrA;
        case TopICR:
          return this.icr;
        default:
          return this.topValue;
      }
    }
    get ocrMask() {
      switch (this.topValue) {
        case TopOCRA:
        case TopICR:
          return 65535;
        default:
          return this.topValue;
      }
    }
    /** Expose the raw value of TCNT, for use by the unit tests */
    get debugTCNT() {
      return this.tcnt;
    }
    updateWGMConfig() {
      const { config, WGM } = this;
      const wgmModes = config.bits === 16 ? wgmModes16Bit : wgmModes8Bit;
      const TCCRA = this.cpu.data[config.TCCRA];
      const [timerMode, topValue, ocrUpdateMode, tovUpdateMode, flags] = wgmModes[WGM];
      this.timerMode = timerMode;
      this.topValue = topValue;
      this.ocrUpdateMode = ocrUpdateMode;
      this.tovUpdateMode = tovUpdateMode;
      const pwmMode = timerMode === FastPWM || timerMode === PWMPhaseCorrect || timerMode === PWMPhaseFrequencyCorrect;
      const prevCompA = this.compA;
      this.compA = TCCRA >> 6 & 3;
      if (this.compA === 1 && pwmMode && !(flags & OCToggle)) {
        this.compA = 0;
      }
      if (!!prevCompA !== !!this.compA) {
        this.updateCompA(this.compA ? PinOverrideMode.Enable : PinOverrideMode.None);
      }
      const prevCompB = this.compB;
      this.compB = TCCRA >> 4 & 3;
      if (this.compB === 1 && pwmMode) {
        this.compB = 0;
      }
      if (!!prevCompB !== !!this.compB) {
        this.updateCompB(this.compB ? PinOverrideMode.Enable : PinOverrideMode.None);
      }
      if (this.hasOCRC) {
        const prevCompC = this.compC;
        this.compC = TCCRA >> 2 & 3;
        if (this.compC === 1 && pwmMode) {
          this.compC = 0;
        }
        if (!!prevCompC !== !!this.compC) {
          this.updateCompC(this.compC ? PinOverrideMode.Enable : PinOverrideMode.None);
        }
      }
    }
    phasePwmCount(value, delta) {
      const { ocrA, ocrB, ocrC, hasOCRC, TOP, MAX, tcntUpdated } = this;
      if (!value && !TOP) {
        delta = 0;
        if (this.ocrUpdateMode === OCRUpdateMode.Top) {
          this.ocrA = this.nextOcrA;
          this.ocrB = this.nextOcrB;
          this.ocrC = this.nextOcrC;
        }
      }
      while (delta > 0) {
        if (this.countingUp) {
          value++;
          if (value === TOP && !tcntUpdated) {
            this.countingUp = false;
            if (this.ocrUpdateMode === OCRUpdateMode.Top) {
              this.ocrA = this.nextOcrA;
              this.ocrB = this.nextOcrB;
              this.ocrC = this.nextOcrC;
            }
          }
        } else {
          value--;
          if (!value && !tcntUpdated) {
            this.countingUp = true;
            this.cpu.setInterruptFlag(this.OVF);
            if (this.ocrUpdateMode === OCRUpdateMode.Bottom) {
              this.ocrA = this.nextOcrA;
              this.ocrB = this.nextOcrB;
              this.ocrC = this.nextOcrC;
            }
          }
        }
        if (!tcntUpdated) {
          if (value === ocrA) {
            this.cpu.setInterruptFlag(this.OCFA);
            if (this.compA) {
              this.updateCompPin(this.compA, "A");
            }
          }
          if (value === ocrB) {
            this.cpu.setInterruptFlag(this.OCFB);
            if (this.compB) {
              this.updateCompPin(this.compB, "B");
            }
          }
          if (hasOCRC && value === ocrC) {
            this.cpu.setInterruptFlag(this.OCFC);
            if (this.compC) {
              this.updateCompPin(this.compC, "C");
            }
          }
        }
        delta--;
      }
      return value & MAX;
    }
    timerUpdated(value, prevValue) {
      const { ocrA, ocrB, ocrC, hasOCRC } = this;
      const overflow = prevValue > value;
      if ((prevValue < ocrA || overflow) && value >= ocrA || prevValue < ocrA && overflow) {
        this.cpu.setInterruptFlag(this.OCFA);
        if (this.compA) {
          this.updateCompPin(this.compA, "A");
        }
      }
      if ((prevValue < ocrB || overflow) && value >= ocrB || prevValue < ocrB && overflow) {
        this.cpu.setInterruptFlag(this.OCFB);
        if (this.compB) {
          this.updateCompPin(this.compB, "B");
        }
      }
      if (hasOCRC && ((prevValue < ocrC || overflow) && value >= ocrC || prevValue < ocrC && overflow)) {
        this.cpu.setInterruptFlag(this.OCFC);
        if (this.compC) {
          this.updateCompPin(this.compC, "C");
        }
      }
    }
    checkForceCompare(value) {
      if (this.timerMode == TimerMode.FastPWM || this.timerMode == TimerMode.PWMPhaseCorrect || this.timerMode == TimerMode.PWMPhaseFrequencyCorrect) {
        return;
      }
      if (value & FOCA) {
        this.updateCompPin(this.compA, "A");
      }
      if (value & FOCB) {
        this.updateCompPin(this.compB, "B");
      }
      if (this.config.compPortC && value & FOCC) {
        this.updateCompPin(this.compC, "C");
      }
    }
    updateCompPin(compValue, pinName, bottom = false) {
      let newValue = PinOverrideMode.None;
      const invertingMode = compValue === 3;
      const isSet = this.countingUp === invertingMode;
      switch (this.timerMode) {
        case Normal:
        case CTC:
          newValue = compToOverride(compValue);
          break;
        case FastPWM:
          if (compValue === 1) {
            newValue = bottom ? PinOverrideMode.None : PinOverrideMode.Toggle;
          } else {
            newValue = invertingMode !== bottom ? PinOverrideMode.Set : PinOverrideMode.Clear;
          }
          break;
        case PWMPhaseCorrect:
        case PWMPhaseFrequencyCorrect:
          if (compValue === 1) {
            newValue = PinOverrideMode.Toggle;
          } else {
            newValue = isSet ? PinOverrideMode.Set : PinOverrideMode.Clear;
          }
          break;
      }
      if (newValue !== PinOverrideMode.None) {
        if (pinName === "A") {
          this.updateCompA(newValue);
        } else if (pinName === "B") {
          this.updateCompB(newValue);
        } else {
          this.updateCompC(newValue);
        }
      }
    }
    updateCompA(value) {
      const { compPortA, compPinA } = this.config;
      const port = this.cpu.gpioByPort[compPortA];
      port === null || port === void 0 ? void 0 : port.timerOverridePin(compPinA, value);
    }
    updateCompB(value) {
      const { compPortB, compPinB } = this.config;
      const port = this.cpu.gpioByPort[compPortB];
      port === null || port === void 0 ? void 0 : port.timerOverridePin(compPinB, value);
    }
    updateCompC(value) {
      const { compPortC, compPinC } = this.config;
      const port = this.cpu.gpioByPort[compPortC];
      port === null || port === void 0 ? void 0 : port.timerOverridePin(compPinC, value);
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/twi.js
  var TWCR_TWINT = 128;
  var TWCR_TWEA = 64;
  var TWCR_TWSTA = 32;
  var TWCR_TWSTO = 16;
  var TWCR_TWEN = 4;
  var TWCR_TWIE = 1;
  var TWSR_TWS_MASK = 248;
  var TWSR_TWPS1 = 2;
  var TWSR_TWPS0 = 1;
  var TWSR_TWPS_MASK = TWSR_TWPS1 | TWSR_TWPS0;
  var STATUS_TWI_IDLE = 248;
  var STATUS_START = 8;
  var STATUS_REPEATED_START = 16;
  var STATUS_SLAW_ACK = 24;
  var STATUS_SLAW_NACK = 32;
  var STATUS_DATA_SENT_ACK = 40;
  var STATUS_DATA_SENT_NACK = 48;
  var STATUS_SLAR_ACK = 64;
  var STATUS_SLAR_NACK = 72;
  var STATUS_DATA_RECEIVED_ACK = 80;
  var STATUS_DATA_RECEIVED_NACK = 88;
  var twiConfig = {
    twiInterrupt: 48,
    TWBR: 184,
    TWSR: 185,
    TWAR: 186,
    TWDR: 187,
    TWCR: 188,
    TWAMR: 189
  };
  var NoopTWIEventHandler = class {
    constructor(twi) {
      this.twi = twi;
    }
    start() {
      this.twi.completeStart();
    }
    stop() {
      this.twi.completeStop();
    }
    connectToSlave() {
      this.twi.completeConnect(false);
    }
    writeByte() {
      this.twi.completeWrite(false);
    }
    readByte() {
      this.twi.completeRead(255);
    }
  };
  var AVRTWI = class {
    constructor(cpu, config, freqHz) {
      this.cpu = cpu;
      this.config = config;
      this.freqHz = freqHz;
      this.eventHandler = new NoopTWIEventHandler(this);
      this.busy = false;
      this.TWI = {
        address: this.config.twiInterrupt,
        flagRegister: this.config.TWCR,
        flagMask: TWCR_TWINT,
        enableRegister: this.config.TWCR,
        enableMask: TWCR_TWIE
      };
      this.updateStatus(STATUS_TWI_IDLE);
      this.cpu.writeHooks[config.TWCR] = (value) => {
        this.cpu.data[config.TWCR] = value;
        const clearInt = value & TWCR_TWINT;
        this.cpu.clearInterruptByFlag(this.TWI, value);
        this.cpu.updateInterruptEnable(this.TWI, value);
        const { status } = this;
        if (clearInt && value & TWCR_TWEN && !this.busy) {
          const twdrValue = this.cpu.data[this.config.TWDR];
          this.cpu.addClockEvent(() => {
            if (value & TWCR_TWSTA) {
              this.busy = true;
              this.eventHandler.start(status !== STATUS_TWI_IDLE);
            } else if (value & TWCR_TWSTO) {
              this.busy = true;
              this.eventHandler.stop();
            } else if (status === STATUS_START || status === STATUS_REPEATED_START) {
              this.busy = true;
              this.eventHandler.connectToSlave(twdrValue >> 1, twdrValue & 1 ? false : true);
            } else if (status === STATUS_SLAW_ACK || status === STATUS_DATA_SENT_ACK) {
              this.busy = true;
              this.eventHandler.writeByte(twdrValue);
            } else if (status === STATUS_SLAR_ACK || status === STATUS_DATA_RECEIVED_ACK) {
              this.busy = true;
              const ack = !!(value & TWCR_TWEA);
              this.eventHandler.readByte(ack);
            }
          }, 0);
          return true;
        }
      };
    }
    get prescaler() {
      switch (this.cpu.data[this.config.TWSR] & TWSR_TWPS_MASK) {
        case 0:
          return 1;
        case 1:
          return 4;
        case 2:
          return 16;
        case 3:
          return 64;
      }
      throw new Error("Invalid prescaler value!");
    }
    get sclFrequency() {
      return this.freqHz / (16 + 2 * this.cpu.data[this.config.TWBR] * this.prescaler);
    }
    completeStart() {
      this.busy = false;
      this.updateStatus(this.status === STATUS_TWI_IDLE ? STATUS_START : STATUS_REPEATED_START);
    }
    completeStop() {
      this.busy = false;
      this.cpu.data[this.config.TWCR] &= ~TWCR_TWSTO;
      this.updateStatus(STATUS_TWI_IDLE);
    }
    completeConnect(ack) {
      this.busy = false;
      if (this.cpu.data[this.config.TWDR] & 1) {
        this.updateStatus(ack ? STATUS_SLAR_ACK : STATUS_SLAR_NACK);
      } else {
        this.updateStatus(ack ? STATUS_SLAW_ACK : STATUS_SLAW_NACK);
      }
    }
    completeWrite(ack) {
      this.busy = false;
      this.updateStatus(ack ? STATUS_DATA_SENT_ACK : STATUS_DATA_SENT_NACK);
    }
    completeRead(value) {
      this.busy = false;
      const ack = !!(this.cpu.data[this.config.TWCR] & TWCR_TWEA);
      this.cpu.data[this.config.TWDR] = value;
      this.updateStatus(ack ? STATUS_DATA_RECEIVED_ACK : STATUS_DATA_RECEIVED_NACK);
    }
    get status() {
      return this.cpu.data[this.config.TWSR] & TWSR_TWS_MASK;
    }
    updateStatus(value) {
      const { TWSR } = this.config;
      this.cpu.data[TWSR] = this.cpu.data[TWSR] & ~TWSR_TWS_MASK | value;
      this.cpu.setInterruptFlag(this.TWI);
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/usart.js
  var usart0Config = {
    rxCompleteInterrupt: 36,
    dataRegisterEmptyInterrupt: 38,
    txCompleteInterrupt: 40,
    UCSRA: 192,
    UCSRB: 193,
    UCSRC: 194,
    UBRRL: 196,
    UBRRH: 197,
    UDR: 198
  };
  var UCSRA_RXC = 128;
  var UCSRA_TXC = 64;
  var UCSRA_UDRE = 32;
  var UCSRA_U2X = 2;
  var UCSRA_MPCM = 1;
  var UCSRA_CFG_MASK = UCSRA_U2X;
  var UCSRB_RXCIE = 128;
  var UCSRB_TXCIE = 64;
  var UCSRB_UDRIE = 32;
  var UCSRB_RXEN = 16;
  var UCSRB_TXEN = 8;
  var UCSRB_UCSZ2 = 4;
  var UCSRB_CFG_MASK = UCSRB_UCSZ2 | UCSRB_RXEN | UCSRB_TXEN;
  var UCSRC_UPM1 = 32;
  var UCSRC_UPM0 = 16;
  var UCSRC_USBS = 8;
  var UCSRC_UCSZ1 = 4;
  var UCSRC_UCSZ0 = 2;
  var rxMasks = {
    5: 31,
    6: 63,
    7: 127,
    8: 255,
    9: 255
  };
  var AVRUSART = class {
    constructor(cpu, config, freqHz) {
      this.cpu = cpu;
      this.config = config;
      this.freqHz = freqHz;
      this.onByteTransmit = null;
      this.onLineTransmit = null;
      this.onRxComplete = null;
      this.onConfigurationChange = null;
      this.rxBusyValue = false;
      this.rxByte = 0;
      this.lineBuffer = "";
      this.RXC = {
        address: this.config.rxCompleteInterrupt,
        flagRegister: this.config.UCSRA,
        flagMask: UCSRA_RXC,
        enableRegister: this.config.UCSRB,
        enableMask: UCSRB_RXCIE,
        constant: true
      };
      this.UDRE = {
        address: this.config.dataRegisterEmptyInterrupt,
        flagRegister: this.config.UCSRA,
        flagMask: UCSRA_UDRE,
        enableRegister: this.config.UCSRB,
        enableMask: UCSRB_UDRIE
      };
      this.TXC = {
        address: this.config.txCompleteInterrupt,
        flagRegister: this.config.UCSRA,
        flagMask: UCSRA_TXC,
        enableRegister: this.config.UCSRB,
        enableMask: UCSRB_TXCIE
      };
      this.reset();
      this.cpu.writeHooks[config.UCSRA] = (value, oldValue) => {
        var _a;
        cpu.data[config.UCSRA] = value & (UCSRA_MPCM | UCSRA_U2X);
        cpu.clearInterruptByFlag(this.TXC, value);
        if ((value & UCSRA_CFG_MASK) !== (oldValue & UCSRA_CFG_MASK)) {
          (_a = this.onConfigurationChange) === null || _a === void 0 ? void 0 : _a.call(this);
        }
        return true;
      };
      this.cpu.writeHooks[config.UCSRB] = (value, oldValue) => {
        var _a;
        cpu.updateInterruptEnable(this.RXC, value);
        cpu.updateInterruptEnable(this.UDRE, value);
        cpu.updateInterruptEnable(this.TXC, value);
        if (value & UCSRB_RXEN && oldValue & UCSRB_RXEN) {
          cpu.clearInterrupt(this.RXC);
        }
        if (value & UCSRB_TXEN && !(oldValue & UCSRB_TXEN)) {
          cpu.setInterruptFlag(this.UDRE);
        }
        cpu.data[config.UCSRB] = value;
        if ((value & UCSRB_CFG_MASK) !== (oldValue & UCSRB_CFG_MASK)) {
          (_a = this.onConfigurationChange) === null || _a === void 0 ? void 0 : _a.call(this);
        }
        return true;
      };
      this.cpu.writeHooks[config.UCSRC] = (value) => {
        var _a;
        cpu.data[config.UCSRC] = value;
        (_a = this.onConfigurationChange) === null || _a === void 0 ? void 0 : _a.call(this);
        return true;
      };
      this.cpu.readHooks[config.UDR] = () => {
        var _a;
        const mask = (_a = rxMasks[this.bitsPerChar]) !== null && _a !== void 0 ? _a : 255;
        const result = this.rxByte & mask;
        this.rxByte = 0;
        this.cpu.clearInterrupt(this.RXC);
        return result;
      };
      this.cpu.writeHooks[config.UDR] = (value) => {
        if (this.onByteTransmit) {
          this.onByteTransmit(value);
        }
        if (this.onLineTransmit) {
          const ch = String.fromCharCode(value);
          if (ch === "\n") {
            this.onLineTransmit(this.lineBuffer);
            this.lineBuffer = "";
          } else {
            this.lineBuffer += ch;
          }
        }
        this.cpu.addClockEvent(() => {
          cpu.setInterruptFlag(this.UDRE);
          cpu.setInterruptFlag(this.TXC);
        }, this.cyclesPerChar);
        this.cpu.clearInterrupt(this.TXC);
        this.cpu.clearInterrupt(this.UDRE);
      };
      this.cpu.writeHooks[config.UBRRH] = (value) => {
        var _a;
        this.cpu.data[config.UBRRH] = value;
        (_a = this.onConfigurationChange) === null || _a === void 0 ? void 0 : _a.call(this);
        return true;
      };
      this.cpu.writeHooks[config.UBRRL] = (value) => {
        var _a;
        this.cpu.data[config.UBRRL] = value;
        (_a = this.onConfigurationChange) === null || _a === void 0 ? void 0 : _a.call(this);
        return true;
      };
    }
    reset() {
      this.cpu.data[this.config.UCSRA] = UCSRA_UDRE;
      this.cpu.data[this.config.UCSRB] = 0;
      this.cpu.data[this.config.UCSRC] = UCSRC_UCSZ1 | UCSRC_UCSZ0;
      this.rxBusyValue = false;
      this.rxByte = 0;
      this.lineBuffer = "";
    }
    get rxBusy() {
      return this.rxBusyValue;
    }
    writeByte(value, immediate = false) {
      var _a;
      const { cpu } = this;
      if (this.rxBusyValue || !this.rxEnable) {
        return false;
      }
      if (immediate) {
        this.rxByte = value;
        cpu.setInterruptFlag(this.RXC);
        (_a = this.onRxComplete) === null || _a === void 0 ? void 0 : _a.call(this);
      } else {
        this.rxBusyValue = true;
        cpu.addClockEvent(() => {
          this.rxBusyValue = false;
          this.writeByte(value, true);
        }, this.cyclesPerChar);
        return true;
      }
    }
    get cyclesPerChar() {
      const symbolsPerChar = 1 + this.bitsPerChar + this.stopBits + (this.parityEnabled ? 1 : 0);
      return (this.UBRR + 1) * this.multiplier * symbolsPerChar;
    }
    get UBRR() {
      const { UBRRH, UBRRL } = this.config;
      return this.cpu.data[UBRRH] << 8 | this.cpu.data[UBRRL];
    }
    get multiplier() {
      return this.cpu.data[this.config.UCSRA] & UCSRA_U2X ? 8 : 16;
    }
    get rxEnable() {
      return !!(this.cpu.data[this.config.UCSRB] & UCSRB_RXEN);
    }
    get txEnable() {
      return !!(this.cpu.data[this.config.UCSRB] & UCSRB_TXEN);
    }
    get baudRate() {
      return Math.floor(this.freqHz / (this.multiplier * (1 + this.UBRR)));
    }
    get bitsPerChar() {
      const ucsz = (this.cpu.data[this.config.UCSRC] & (UCSRC_UCSZ1 | UCSRC_UCSZ0)) >> 1 | this.cpu.data[this.config.UCSRB] & UCSRB_UCSZ2;
      switch (ucsz) {
        case 0:
          return 5;
        case 1:
          return 6;
        case 2:
          return 7;
        case 3:
          return 8;
        default:
        // 4..6 are reserved
        case 7:
          return 9;
      }
    }
    get stopBits() {
      return this.cpu.data[this.config.UCSRC] & UCSRC_USBS ? 2 : 1;
    }
    get parityEnabled() {
      return this.cpu.data[this.config.UCSRC] & UCSRC_UPM1 ? true : false;
    }
    get parityOdd() {
      return this.cpu.data[this.config.UCSRC] & UCSRC_UPM0 ? true : false;
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/usi.js
  var USICR = 45;
  var USISR = 46;
  var USIDR = 47;
  var USIBR = 48;
  var USICNT_MASK = 15;
  var USIDC = 1 << 4;
  var USIPF = 1 << 5;
  var USIOIF = 1 << 6;
  var USISIF = 1 << 7;
  var USITC = 1 << 0;
  var USICLK = 1 << 1;
  var USICS0 = 1 << 2;
  var USICS1 = 1 << 3;
  var USIWM0 = 1 << 4;
  var USIWM1 = 1 << 5;
  var USIOIE = 1 << 6;
  var USISIE = 1 << 7;
  var AVRUSI = class {
    constructor(cpu, port, portPin, dataPin, clockPin) {
      this.START = {
        address: 13,
        flagRegister: USISR,
        flagMask: USISIF,
        enableRegister: USICR,
        enableMask: USISIE
      };
      this.OVF = {
        address: 14,
        flagRegister: USISR,
        flagMask: USIOIF,
        enableRegister: USICR,
        enableMask: USIOIE
      };
      const PIN = portPin;
      const PORT = PIN + 2;
      port.addListener((value) => {
        const twoWire = (cpu.data[USICR] & USIWM1) === USIWM1;
        if (twoWire) {
          if (value & 1 << clockPin && !(value & 1 << dataPin)) {
            cpu.setInterruptFlag(this.START);
          }
          if (value & 1 << clockPin && value & 1 << dataPin) {
            cpu.data[USISR] |= USIPF;
          }
        }
      });
      const updateOutput = () => {
        const oldValue = cpu.data[PORT];
        const newValue = cpu.data[USIDR] & 128 ? oldValue | 1 << dataPin : oldValue & ~(1 << dataPin);
        cpu.writeHooks[PORT](newValue, oldValue, PORT, 255);
        if (newValue & 128 && !(cpu.data[PIN] & 128)) {
          cpu.data[USISR] |= USIDC;
        } else {
          cpu.data[USISR] &= ~USIDC;
        }
      };
      const count = () => {
        const counter = cpu.data[USISR] + 1 & USICNT_MASK;
        cpu.data[USISR] = cpu.data[USISR] & ~USICNT_MASK | counter;
        if (!counter) {
          cpu.data[USIBR] = cpu.data[USIDR];
          cpu.setInterruptFlag(this.OVF);
        }
      };
      const shift = (inputValue) => {
        cpu.data[USIDR] = cpu.data[USIDR] << 1 | inputValue;
        updateOutput();
      };
      cpu.writeHooks[USIDR] = (value) => {
        cpu.data[USIDR] = value;
        updateOutput();
        return true;
      };
      cpu.writeHooks[USISR] = (value) => {
        const writeClearMask = USISIF | USIOIF | USIPF;
        cpu.data[USISR] = cpu.data[USISR] & writeClearMask & ~value | value & 15;
        cpu.clearInterruptByFlag(this.START, value);
        cpu.clearInterruptByFlag(this.OVF, value);
        return true;
      };
      cpu.writeHooks[USICR] = (value) => {
        cpu.data[USICR] = value & ~(USICLK | USITC);
        cpu.updateInterruptEnable(this.START, value);
        cpu.updateInterruptEnable(this.OVF, value);
        const clockSrc = value & (USICS1 | USICS0) >> 2;
        const mode = value & (USIWM1 | USIWM0) >> 4;
        const usiClk = value & USICLK;
        port.openCollector = mode >= 2 ? 1 << dataPin : 0;
        const inputValue = cpu.data[PIN] & 1 << dataPin ? 1 : 0;
        if (usiClk && !clockSrc) {
          shift(inputValue);
          count();
        }
        if (value & USITC) {
          cpu.writeHooks[PIN](1 << clockPin, cpu.data[PIN], PIN, 255);
          const newValue = cpu.data[PIN] & 1 << clockPin;
          if (usiClk && (clockSrc === 2 || clockSrc === 3)) {
            if (clockSrc === 2 && newValue) {
              shift(inputValue);
            }
            if (clockSrc === 3 && !newValue) {
              shift(inputValue);
            }
            count();
          }
          return true;
        }
      };
    }
  };

  // node_modules/avr8js/dist/esm/peripherals/watchdog.js
  var MCUSR_WDRF = 8;
  var WDTCSR_WDIF = 128;
  var WDTCSR_WDIE = 64;
  var WDTCSR_WDP3 = 32;
  var WDTCSR_WDCE = 16;
  var WDTCSR_WDE = 8;
  var WDTCSR_WDP2 = 4;
  var WDTCSR_WDP1 = 2;
  var WDTCSR_WDP0 = 1;
  var WDTCSR_WDP210 = WDTCSR_WDP2 | WDTCSR_WDP1 | WDTCSR_WDP0;
  var WDTCSR_PROTECT_MASK = WDTCSR_WDE | WDTCSR_WDP3 | WDTCSR_WDP210;
  var watchdogConfig = {
    watchdogInterrupt: 12,
    MCUSR: 84,
    WDTCSR: 96
  };
  var AVRWatchdog = class {
    constructor(cpu, config, clock) {
      this.cpu = cpu;
      this.config = config;
      this.clock = clock;
      this.clockFrequency = 128e3;
      this.changeEnabledCycles = 0;
      this.watchdogTimeout = 0;
      this.enabledValue = false;
      this.scheduled = false;
      this.Watchdog = {
        address: this.config.watchdogInterrupt,
        flagRegister: this.config.WDTCSR,
        flagMask: WDTCSR_WDIF,
        enableRegister: this.config.WDTCSR,
        enableMask: WDTCSR_WDIE
      };
      this.checkWatchdog = () => {
        if (this.enabled && this.cpu.cycles >= this.watchdogTimeout) {
          const wdtcsr = this.cpu.data[this.config.WDTCSR];
          if (wdtcsr & WDTCSR_WDIE) {
            this.cpu.setInterruptFlag(this.Watchdog);
          }
          if (wdtcsr & WDTCSR_WDE) {
            if (wdtcsr & WDTCSR_WDIE) {
              this.cpu.data[this.config.WDTCSR] &= ~WDTCSR_WDIE;
            } else {
              this.cpu.reset();
              this.scheduled = false;
              this.cpu.data[this.config.MCUSR] |= MCUSR_WDRF;
              return;
            }
          }
          this.resetWatchdog();
        }
        if (this.enabled) {
          this.scheduled = true;
          this.cpu.addClockEvent(this.checkWatchdog, this.watchdogTimeout - this.cpu.cycles);
        } else {
          this.scheduled = false;
        }
      };
      const { WDTCSR } = config;
      this.cpu.onWatchdogReset = () => {
        this.resetWatchdog();
      };
      cpu.writeHooks[WDTCSR] = (value, oldValue) => {
        if (value & WDTCSR_WDCE && value & WDTCSR_WDE) {
          this.changeEnabledCycles = this.cpu.cycles + 4;
          value = value & ~WDTCSR_PROTECT_MASK;
        } else {
          if (this.cpu.cycles >= this.changeEnabledCycles) {
            value = value & ~WDTCSR_PROTECT_MASK | oldValue & WDTCSR_PROTECT_MASK;
          }
          this.enabledValue = !!(value & WDTCSR_WDE || value & WDTCSR_WDIE);
          this.cpu.data[WDTCSR] = value;
        }
        if (this.enabled) {
          this.resetWatchdog();
        }
        if (this.enabled && !this.scheduled) {
          this.cpu.addClockEvent(this.checkWatchdog, this.watchdogTimeout - this.cpu.cycles);
        }
        this.cpu.clearInterruptByFlag(this.Watchdog, value);
        return true;
      };
    }
    resetWatchdog() {
      const cycles = Math.floor(this.clock.frequency / this.clockFrequency * this.prescaler);
      this.watchdogTimeout = this.cpu.cycles + cycles;
    }
    get enabled() {
      return this.enabledValue;
    }
    /**
     * The base clock frequency is 128KHz. Thus, a prescaler of 2048 gives 16ms timeout.
     */
    get prescaler() {
      const wdtcsr = this.cpu.data[this.config.WDTCSR];
      const value = (wdtcsr & WDTCSR_WDP3) >> 2 | wdtcsr & WDTCSR_WDP210;
      return 2048 << value;
    }
  };
  return __toCommonJS(index_exports);
})();
