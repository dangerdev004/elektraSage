(() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
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
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // node_modules/base64-js/index.js
  var require_base64_js = __commonJS({
    "node_modules/base64-js/index.js"(exports) {
      "use strict";
      exports.byteLength = byteLength;
      exports.toByteArray = toByteArray;
      exports.fromByteArray = fromByteArray;
      var lookup = [];
      var revLookup = [];
      var Arr = typeof Uint8Array !== "undefined" ? Uint8Array : Array;
      var code = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
      for (i = 0, len = code.length; i < len; ++i) {
        lookup[i] = code[i];
        revLookup[code.charCodeAt(i)] = i;
      }
      var i;
      var len;
      revLookup["-".charCodeAt(0)] = 62;
      revLookup["_".charCodeAt(0)] = 63;
      function getLens(b64) {
        var len2 = b64.length;
        if (len2 % 4 > 0) {
          throw new Error("Invalid string. Length must be a multiple of 4");
        }
        var validLen = b64.indexOf("=");
        if (validLen === -1) validLen = len2;
        var placeHoldersLen = validLen === len2 ? 0 : 4 - validLen % 4;
        return [validLen, placeHoldersLen];
      }
      function byteLength(b64) {
        var lens = getLens(b64);
        var validLen = lens[0];
        var placeHoldersLen = lens[1];
        return (validLen + placeHoldersLen) * 3 / 4 - placeHoldersLen;
      }
      function _byteLength(b64, validLen, placeHoldersLen) {
        return (validLen + placeHoldersLen) * 3 / 4 - placeHoldersLen;
      }
      function toByteArray(b64) {
        var tmp;
        var lens = getLens(b64);
        var validLen = lens[0];
        var placeHoldersLen = lens[1];
        var arr = new Arr(_byteLength(b64, validLen, placeHoldersLen));
        var curByte = 0;
        var len2 = placeHoldersLen > 0 ? validLen - 4 : validLen;
        var i2;
        for (i2 = 0; i2 < len2; i2 += 4) {
          tmp = revLookup[b64.charCodeAt(i2)] << 18 | revLookup[b64.charCodeAt(i2 + 1)] << 12 | revLookup[b64.charCodeAt(i2 + 2)] << 6 | revLookup[b64.charCodeAt(i2 + 3)];
          arr[curByte++] = tmp >> 16 & 255;
          arr[curByte++] = tmp >> 8 & 255;
          arr[curByte++] = tmp & 255;
        }
        if (placeHoldersLen === 2) {
          tmp = revLookup[b64.charCodeAt(i2)] << 2 | revLookup[b64.charCodeAt(i2 + 1)] >> 4;
          arr[curByte++] = tmp & 255;
        }
        if (placeHoldersLen === 1) {
          tmp = revLookup[b64.charCodeAt(i2)] << 10 | revLookup[b64.charCodeAt(i2 + 1)] << 4 | revLookup[b64.charCodeAt(i2 + 2)] >> 2;
          arr[curByte++] = tmp >> 8 & 255;
          arr[curByte++] = tmp & 255;
        }
        return arr;
      }
      function tripletToBase64(num) {
        return lookup[num >> 18 & 63] + lookup[num >> 12 & 63] + lookup[num >> 6 & 63] + lookup[num & 63];
      }
      function encodeChunk(uint8, start, end) {
        var tmp;
        var output = [];
        for (var i2 = start; i2 < end; i2 += 3) {
          tmp = (uint8[i2] << 16 & 16711680) + (uint8[i2 + 1] << 8 & 65280) + (uint8[i2 + 2] & 255);
          output.push(tripletToBase64(tmp));
        }
        return output.join("");
      }
      function fromByteArray(uint8) {
        var tmp;
        var len2 = uint8.length;
        var extraBytes = len2 % 3;
        var parts = [];
        var maxChunkLength = 16383;
        for (var i2 = 0, len22 = len2 - extraBytes; i2 < len22; i2 += maxChunkLength) {
          parts.push(encodeChunk(uint8, i2, i2 + maxChunkLength > len22 ? len22 : i2 + maxChunkLength));
        }
        if (extraBytes === 1) {
          tmp = uint8[len2 - 1];
          parts.push(
            lookup[tmp >> 2] + lookup[tmp << 4 & 63] + "=="
          );
        } else if (extraBytes === 2) {
          tmp = (uint8[len2 - 2] << 8) + uint8[len2 - 1];
          parts.push(
            lookup[tmp >> 10] + lookup[tmp >> 4 & 63] + lookup[tmp << 2 & 63] + "="
          );
        }
        return parts.join("");
      }
    }
  });

  // node_modules/ieee754/index.js
  var require_ieee754 = __commonJS({
    "node_modules/ieee754/index.js"(exports) {
      exports.read = function(buffer, offset, isLE, mLen, nBytes) {
        var e, m;
        var eLen = nBytes * 8 - mLen - 1;
        var eMax = (1 << eLen) - 1;
        var eBias = eMax >> 1;
        var nBits = -7;
        var i = isLE ? nBytes - 1 : 0;
        var d = isLE ? -1 : 1;
        var s = buffer[offset + i];
        i += d;
        e = s & (1 << -nBits) - 1;
        s >>= -nBits;
        nBits += eLen;
        for (; nBits > 0; e = e * 256 + buffer[offset + i], i += d, nBits -= 8) {
        }
        m = e & (1 << -nBits) - 1;
        e >>= -nBits;
        nBits += mLen;
        for (; nBits > 0; m = m * 256 + buffer[offset + i], i += d, nBits -= 8) {
        }
        if (e === 0) {
          e = 1 - eBias;
        } else if (e === eMax) {
          return m ? NaN : (s ? -1 : 1) * Infinity;
        } else {
          m = m + Math.pow(2, mLen);
          e = e - eBias;
        }
        return (s ? -1 : 1) * m * Math.pow(2, e - mLen);
      };
      exports.write = function(buffer, value, offset, isLE, mLen, nBytes) {
        var e, m, c;
        var eLen = nBytes * 8 - mLen - 1;
        var eMax = (1 << eLen) - 1;
        var eBias = eMax >> 1;
        var rt = mLen === 23 ? Math.pow(2, -24) - Math.pow(2, -77) : 0;
        var i = isLE ? 0 : nBytes - 1;
        var d = isLE ? 1 : -1;
        var s = value < 0 || value === 0 && 1 / value < 0 ? 1 : 0;
        value = Math.abs(value);
        if (isNaN(value) || value === Infinity) {
          m = isNaN(value) ? 1 : 0;
          e = eMax;
        } else {
          e = Math.floor(Math.log(value) / Math.LN2);
          if (value * (c = Math.pow(2, -e)) < 1) {
            e--;
            c *= 2;
          }
          if (e + eBias >= 1) {
            value += rt / c;
          } else {
            value += rt * Math.pow(2, 1 - eBias);
          }
          if (value * c >= 2) {
            e++;
            c /= 2;
          }
          if (e + eBias >= eMax) {
            m = 0;
            e = eMax;
          } else if (e + eBias >= 1) {
            m = (value * c - 1) * Math.pow(2, mLen);
            e = e + eBias;
          } else {
            m = value * Math.pow(2, eBias - 1) * Math.pow(2, mLen);
            e = 0;
          }
        }
        for (; mLen >= 8; buffer[offset + i] = m & 255, i += d, m /= 256, mLen -= 8) {
        }
        e = e << mLen | m;
        eLen += mLen;
        for (; eLen > 0; buffer[offset + i] = e & 255, i += d, e /= 256, eLen -= 8) {
        }
        buffer[offset + i - d] |= s * 128;
      };
    }
  });

  // node_modules/buffer/index.js
  var require_buffer = __commonJS({
    "node_modules/buffer/index.js"(exports) {
      "use strict";
      var base64 = require_base64_js();
      var ieee754 = require_ieee754();
      var customInspectSymbol = typeof Symbol === "function" && typeof Symbol["for"] === "function" ? Symbol["for"]("nodejs.util.inspect.custom") : null;
      exports.Buffer = Buffer3;
      exports.SlowBuffer = SlowBuffer;
      exports.INSPECT_MAX_BYTES = 50;
      var K_MAX_LENGTH = 2147483647;
      exports.kMaxLength = K_MAX_LENGTH;
      Buffer3.TYPED_ARRAY_SUPPORT = typedArraySupport();
      if (!Buffer3.TYPED_ARRAY_SUPPORT && typeof console !== "undefined" && typeof console.error === "function") {
        console.error(
          "This browser lacks typed array (Uint8Array) support which is required by `buffer` v5.x. Use `buffer` v4.x if you require old browser support."
        );
      }
      function typedArraySupport() {
        try {
          const arr = new Uint8Array(1);
          const proto = { foo: function() {
            return 42;
          } };
          Object.setPrototypeOf(proto, Uint8Array.prototype);
          Object.setPrototypeOf(arr, proto);
          return arr.foo() === 42;
        } catch (e) {
          return false;
        }
      }
      Object.defineProperty(Buffer3.prototype, "parent", {
        enumerable: true,
        get: function() {
          if (!Buffer3.isBuffer(this)) return void 0;
          return this.buffer;
        }
      });
      Object.defineProperty(Buffer3.prototype, "offset", {
        enumerable: true,
        get: function() {
          if (!Buffer3.isBuffer(this)) return void 0;
          return this.byteOffset;
        }
      });
      function createBuffer(length) {
        if (length > K_MAX_LENGTH) {
          throw new RangeError('The value "' + length + '" is invalid for option "size"');
        }
        const buf = new Uint8Array(length);
        Object.setPrototypeOf(buf, Buffer3.prototype);
        return buf;
      }
      function Buffer3(arg, encodingOrOffset, length) {
        if (typeof arg === "number") {
          if (typeof encodingOrOffset === "string") {
            throw new TypeError(
              'The "string" argument must be of type string. Received type number'
            );
          }
          return allocUnsafe(arg);
        }
        return from(arg, encodingOrOffset, length);
      }
      Buffer3.poolSize = 8192;
      function from(value, encodingOrOffset, length) {
        if (typeof value === "string") {
          return fromString(value, encodingOrOffset);
        }
        if (ArrayBuffer.isView(value)) {
          return fromArrayView(value);
        }
        if (value == null) {
          throw new TypeError(
            "The first argument must be one of type string, Buffer, ArrayBuffer, Array, or Array-like Object. Received type " + typeof value
          );
        }
        if (isInstance(value, ArrayBuffer) || value && isInstance(value.buffer, ArrayBuffer)) {
          return fromArrayBuffer(value, encodingOrOffset, length);
        }
        if (typeof SharedArrayBuffer !== "undefined" && (isInstance(value, SharedArrayBuffer) || value && isInstance(value.buffer, SharedArrayBuffer))) {
          return fromArrayBuffer(value, encodingOrOffset, length);
        }
        if (typeof value === "number") {
          throw new TypeError(
            'The "value" argument must not be of type number. Received type number'
          );
        }
        const valueOf = value.valueOf && value.valueOf();
        if (valueOf != null && valueOf !== value) {
          return Buffer3.from(valueOf, encodingOrOffset, length);
        }
        const b = fromObject(value);
        if (b) return b;
        if (typeof Symbol !== "undefined" && Symbol.toPrimitive != null && typeof value[Symbol.toPrimitive] === "function") {
          return Buffer3.from(value[Symbol.toPrimitive]("string"), encodingOrOffset, length);
        }
        throw new TypeError(
          "The first argument must be one of type string, Buffer, ArrayBuffer, Array, or Array-like Object. Received type " + typeof value
        );
      }
      Buffer3.from = function(value, encodingOrOffset, length) {
        return from(value, encodingOrOffset, length);
      };
      Object.setPrototypeOf(Buffer3.prototype, Uint8Array.prototype);
      Object.setPrototypeOf(Buffer3, Uint8Array);
      function assertSize(size) {
        if (typeof size !== "number") {
          throw new TypeError('"size" argument must be of type number');
        } else if (size < 0) {
          throw new RangeError('The value "' + size + '" is invalid for option "size"');
        }
      }
      function alloc(size, fill, encoding) {
        assertSize(size);
        if (size <= 0) {
          return createBuffer(size);
        }
        if (fill !== void 0) {
          return typeof encoding === "string" ? createBuffer(size).fill(fill, encoding) : createBuffer(size).fill(fill);
        }
        return createBuffer(size);
      }
      Buffer3.alloc = function(size, fill, encoding) {
        return alloc(size, fill, encoding);
      };
      function allocUnsafe(size) {
        assertSize(size);
        return createBuffer(size < 0 ? 0 : checked(size) | 0);
      }
      Buffer3.allocUnsafe = function(size) {
        return allocUnsafe(size);
      };
      Buffer3.allocUnsafeSlow = function(size) {
        return allocUnsafe(size);
      };
      function fromString(string, encoding) {
        if (typeof encoding !== "string" || encoding === "") {
          encoding = "utf8";
        }
        if (!Buffer3.isEncoding(encoding)) {
          throw new TypeError("Unknown encoding: " + encoding);
        }
        const length = byteLength(string, encoding) | 0;
        let buf = createBuffer(length);
        const actual = buf.write(string, encoding);
        if (actual !== length) {
          buf = buf.slice(0, actual);
        }
        return buf;
      }
      function fromArrayLike(array) {
        const length = array.length < 0 ? 0 : checked(array.length) | 0;
        const buf = createBuffer(length);
        for (let i = 0; i < length; i += 1) {
          buf[i] = array[i] & 255;
        }
        return buf;
      }
      function fromArrayView(arrayView) {
        if (isInstance(arrayView, Uint8Array)) {
          const copy = new Uint8Array(arrayView);
          return fromArrayBuffer(copy.buffer, copy.byteOffset, copy.byteLength);
        }
        return fromArrayLike(arrayView);
      }
      function fromArrayBuffer(array, byteOffset, length) {
        if (byteOffset < 0 || array.byteLength < byteOffset) {
          throw new RangeError('"offset" is outside of buffer bounds');
        }
        if (array.byteLength < byteOffset + (length || 0)) {
          throw new RangeError('"length" is outside of buffer bounds');
        }
        let buf;
        if (byteOffset === void 0 && length === void 0) {
          buf = new Uint8Array(array);
        } else if (length === void 0) {
          buf = new Uint8Array(array, byteOffset);
        } else {
          buf = new Uint8Array(array, byteOffset, length);
        }
        Object.setPrototypeOf(buf, Buffer3.prototype);
        return buf;
      }
      function fromObject(obj) {
        if (Buffer3.isBuffer(obj)) {
          const len = checked(obj.length) | 0;
          const buf = createBuffer(len);
          if (buf.length === 0) {
            return buf;
          }
          obj.copy(buf, 0, 0, len);
          return buf;
        }
        if (obj.length !== void 0) {
          if (typeof obj.length !== "number" || numberIsNaN(obj.length)) {
            return createBuffer(0);
          }
          return fromArrayLike(obj);
        }
        if (obj.type === "Buffer" && Array.isArray(obj.data)) {
          return fromArrayLike(obj.data);
        }
      }
      function checked(length) {
        if (length >= K_MAX_LENGTH) {
          throw new RangeError("Attempt to allocate Buffer larger than maximum size: 0x" + K_MAX_LENGTH.toString(16) + " bytes");
        }
        return length | 0;
      }
      function SlowBuffer(length) {
        if (+length != length) {
          length = 0;
        }
        return Buffer3.alloc(+length);
      }
      Buffer3.isBuffer = function isBuffer(b) {
        return b != null && b._isBuffer === true && b !== Buffer3.prototype;
      };
      Buffer3.compare = function compare(a, b) {
        if (isInstance(a, Uint8Array)) a = Buffer3.from(a, a.offset, a.byteLength);
        if (isInstance(b, Uint8Array)) b = Buffer3.from(b, b.offset, b.byteLength);
        if (!Buffer3.isBuffer(a) || !Buffer3.isBuffer(b)) {
          throw new TypeError(
            'The "buf1", "buf2" arguments must be one of type Buffer or Uint8Array'
          );
        }
        if (a === b) return 0;
        let x = a.length;
        let y = b.length;
        for (let i = 0, len = Math.min(x, y); i < len; ++i) {
          if (a[i] !== b[i]) {
            x = a[i];
            y = b[i];
            break;
          }
        }
        if (x < y) return -1;
        if (y < x) return 1;
        return 0;
      };
      Buffer3.isEncoding = function isEncoding(encoding) {
        switch (String(encoding).toLowerCase()) {
          case "hex":
          case "utf8":
          case "utf-8":
          case "ascii":
          case "latin1":
          case "binary":
          case "base64":
          case "ucs2":
          case "ucs-2":
          case "utf16le":
          case "utf-16le":
            return true;
          default:
            return false;
        }
      };
      Buffer3.concat = function concat(list, length) {
        if (!Array.isArray(list)) {
          throw new TypeError('"list" argument must be an Array of Buffers');
        }
        if (list.length === 0) {
          return Buffer3.alloc(0);
        }
        let i;
        if (length === void 0) {
          length = 0;
          for (i = 0; i < list.length; ++i) {
            length += list[i].length;
          }
        }
        const buffer = Buffer3.allocUnsafe(length);
        let pos = 0;
        for (i = 0; i < list.length; ++i) {
          let buf = list[i];
          if (isInstance(buf, Uint8Array)) {
            if (pos + buf.length > buffer.length) {
              if (!Buffer3.isBuffer(buf)) buf = Buffer3.from(buf);
              buf.copy(buffer, pos);
            } else {
              Uint8Array.prototype.set.call(
                buffer,
                buf,
                pos
              );
            }
          } else if (!Buffer3.isBuffer(buf)) {
            throw new TypeError('"list" argument must be an Array of Buffers');
          } else {
            buf.copy(buffer, pos);
          }
          pos += buf.length;
        }
        return buffer;
      };
      function byteLength(string, encoding) {
        if (Buffer3.isBuffer(string)) {
          return string.length;
        }
        if (ArrayBuffer.isView(string) || isInstance(string, ArrayBuffer)) {
          return string.byteLength;
        }
        if (typeof string !== "string") {
          throw new TypeError(
            'The "string" argument must be one of type string, Buffer, or ArrayBuffer. Received type ' + typeof string
          );
        }
        const len = string.length;
        const mustMatch = arguments.length > 2 && arguments[2] === true;
        if (!mustMatch && len === 0) return 0;
        let loweredCase = false;
        for (; ; ) {
          switch (encoding) {
            case "ascii":
            case "latin1":
            case "binary":
              return len;
            case "utf8":
            case "utf-8":
              return utf8ToBytes(string).length;
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return len * 2;
            case "hex":
              return len >>> 1;
            case "base64":
              return base64ToBytes(string).length;
            default:
              if (loweredCase) {
                return mustMatch ? -1 : utf8ToBytes(string).length;
              }
              encoding = ("" + encoding).toLowerCase();
              loweredCase = true;
          }
        }
      }
      Buffer3.byteLength = byteLength;
      function slowToString(encoding, start, end) {
        let loweredCase = false;
        if (start === void 0 || start < 0) {
          start = 0;
        }
        if (start > this.length) {
          return "";
        }
        if (end === void 0 || end > this.length) {
          end = this.length;
        }
        if (end <= 0) {
          return "";
        }
        end >>>= 0;
        start >>>= 0;
        if (end <= start) {
          return "";
        }
        if (!encoding) encoding = "utf8";
        while (true) {
          switch (encoding) {
            case "hex":
              return hexSlice(this, start, end);
            case "utf8":
            case "utf-8":
              return utf8Slice(this, start, end);
            case "ascii":
              return asciiSlice(this, start, end);
            case "latin1":
            case "binary":
              return latin1Slice(this, start, end);
            case "base64":
              return base64Slice(this, start, end);
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return utf16leSlice(this, start, end);
            default:
              if (loweredCase) throw new TypeError("Unknown encoding: " + encoding);
              encoding = (encoding + "").toLowerCase();
              loweredCase = true;
          }
        }
      }
      Buffer3.prototype._isBuffer = true;
      function swap(b, n, m) {
        const i = b[n];
        b[n] = b[m];
        b[m] = i;
      }
      Buffer3.prototype.swap16 = function swap16() {
        const len = this.length;
        if (len % 2 !== 0) {
          throw new RangeError("Buffer size must be a multiple of 16-bits");
        }
        for (let i = 0; i < len; i += 2) {
          swap(this, i, i + 1);
        }
        return this;
      };
      Buffer3.prototype.swap32 = function swap32() {
        const len = this.length;
        if (len % 4 !== 0) {
          throw new RangeError("Buffer size must be a multiple of 32-bits");
        }
        for (let i = 0; i < len; i += 4) {
          swap(this, i, i + 3);
          swap(this, i + 1, i + 2);
        }
        return this;
      };
      Buffer3.prototype.swap64 = function swap64() {
        const len = this.length;
        if (len % 8 !== 0) {
          throw new RangeError("Buffer size must be a multiple of 64-bits");
        }
        for (let i = 0; i < len; i += 8) {
          swap(this, i, i + 7);
          swap(this, i + 1, i + 6);
          swap(this, i + 2, i + 5);
          swap(this, i + 3, i + 4);
        }
        return this;
      };
      Buffer3.prototype.toString = function toString() {
        const length = this.length;
        if (length === 0) return "";
        if (arguments.length === 0) return utf8Slice(this, 0, length);
        return slowToString.apply(this, arguments);
      };
      Buffer3.prototype.toLocaleString = Buffer3.prototype.toString;
      Buffer3.prototype.equals = function equals(b) {
        if (!Buffer3.isBuffer(b)) throw new TypeError("Argument must be a Buffer");
        if (this === b) return true;
        return Buffer3.compare(this, b) === 0;
      };
      Buffer3.prototype.inspect = function inspect() {
        let str = "";
        const max = exports.INSPECT_MAX_BYTES;
        str = this.toString("hex", 0, max).replace(/(.{2})/g, "$1 ").trim();
        if (this.length > max) str += " ... ";
        return "<Buffer " + str + ">";
      };
      if (customInspectSymbol) {
        Buffer3.prototype[customInspectSymbol] = Buffer3.prototype.inspect;
      }
      Buffer3.prototype.compare = function compare(target, start, end, thisStart, thisEnd) {
        if (isInstance(target, Uint8Array)) {
          target = Buffer3.from(target, target.offset, target.byteLength);
        }
        if (!Buffer3.isBuffer(target)) {
          throw new TypeError(
            'The "target" argument must be one of type Buffer or Uint8Array. Received type ' + typeof target
          );
        }
        if (start === void 0) {
          start = 0;
        }
        if (end === void 0) {
          end = target ? target.length : 0;
        }
        if (thisStart === void 0) {
          thisStart = 0;
        }
        if (thisEnd === void 0) {
          thisEnd = this.length;
        }
        if (start < 0 || end > target.length || thisStart < 0 || thisEnd > this.length) {
          throw new RangeError("out of range index");
        }
        if (thisStart >= thisEnd && start >= end) {
          return 0;
        }
        if (thisStart >= thisEnd) {
          return -1;
        }
        if (start >= end) {
          return 1;
        }
        start >>>= 0;
        end >>>= 0;
        thisStart >>>= 0;
        thisEnd >>>= 0;
        if (this === target) return 0;
        let x = thisEnd - thisStart;
        let y = end - start;
        const len = Math.min(x, y);
        const thisCopy = this.slice(thisStart, thisEnd);
        const targetCopy = target.slice(start, end);
        for (let i = 0; i < len; ++i) {
          if (thisCopy[i] !== targetCopy[i]) {
            x = thisCopy[i];
            y = targetCopy[i];
            break;
          }
        }
        if (x < y) return -1;
        if (y < x) return 1;
        return 0;
      };
      function bidirectionalIndexOf(buffer, val, byteOffset, encoding, dir) {
        if (buffer.length === 0) return -1;
        if (typeof byteOffset === "string") {
          encoding = byteOffset;
          byteOffset = 0;
        } else if (byteOffset > 2147483647) {
          byteOffset = 2147483647;
        } else if (byteOffset < -2147483648) {
          byteOffset = -2147483648;
        }
        byteOffset = +byteOffset;
        if (numberIsNaN(byteOffset)) {
          byteOffset = dir ? 0 : buffer.length - 1;
        }
        if (byteOffset < 0) byteOffset = buffer.length + byteOffset;
        if (byteOffset >= buffer.length) {
          if (dir) return -1;
          else byteOffset = buffer.length - 1;
        } else if (byteOffset < 0) {
          if (dir) byteOffset = 0;
          else return -1;
        }
        if (typeof val === "string") {
          val = Buffer3.from(val, encoding);
        }
        if (Buffer3.isBuffer(val)) {
          if (val.length === 0) {
            return -1;
          }
          return arrayIndexOf(buffer, val, byteOffset, encoding, dir);
        } else if (typeof val === "number") {
          val = val & 255;
          if (typeof Uint8Array.prototype.indexOf === "function") {
            if (dir) {
              return Uint8Array.prototype.indexOf.call(buffer, val, byteOffset);
            } else {
              return Uint8Array.prototype.lastIndexOf.call(buffer, val, byteOffset);
            }
          }
          return arrayIndexOf(buffer, [val], byteOffset, encoding, dir);
        }
        throw new TypeError("val must be string, number or Buffer");
      }
      function arrayIndexOf(arr, val, byteOffset, encoding, dir) {
        let indexSize = 1;
        let arrLength = arr.length;
        let valLength = val.length;
        if (encoding !== void 0) {
          encoding = String(encoding).toLowerCase();
          if (encoding === "ucs2" || encoding === "ucs-2" || encoding === "utf16le" || encoding === "utf-16le") {
            if (arr.length < 2 || val.length < 2) {
              return -1;
            }
            indexSize = 2;
            arrLength /= 2;
            valLength /= 2;
            byteOffset /= 2;
          }
        }
        function read(buf, i2) {
          if (indexSize === 1) {
            return buf[i2];
          } else {
            return buf.readUInt16BE(i2 * indexSize);
          }
        }
        let i;
        if (dir) {
          let foundIndex = -1;
          for (i = byteOffset; i < arrLength; i++) {
            if (read(arr, i) === read(val, foundIndex === -1 ? 0 : i - foundIndex)) {
              if (foundIndex === -1) foundIndex = i;
              if (i - foundIndex + 1 === valLength) return foundIndex * indexSize;
            } else {
              if (foundIndex !== -1) i -= i - foundIndex;
              foundIndex = -1;
            }
          }
        } else {
          if (byteOffset + valLength > arrLength) byteOffset = arrLength - valLength;
          for (i = byteOffset; i >= 0; i--) {
            let found = true;
            for (let j = 0; j < valLength; j++) {
              if (read(arr, i + j) !== read(val, j)) {
                found = false;
                break;
              }
            }
            if (found) return i;
          }
        }
        return -1;
      }
      Buffer3.prototype.includes = function includes(val, byteOffset, encoding) {
        return this.indexOf(val, byteOffset, encoding) !== -1;
      };
      Buffer3.prototype.indexOf = function indexOf(val, byteOffset, encoding) {
        return bidirectionalIndexOf(this, val, byteOffset, encoding, true);
      };
      Buffer3.prototype.lastIndexOf = function lastIndexOf(val, byteOffset, encoding) {
        return bidirectionalIndexOf(this, val, byteOffset, encoding, false);
      };
      function hexWrite(buf, string, offset, length) {
        offset = Number(offset) || 0;
        const remaining = buf.length - offset;
        if (!length) {
          length = remaining;
        } else {
          length = Number(length);
          if (length > remaining) {
            length = remaining;
          }
        }
        const strLen = string.length;
        if (length > strLen / 2) {
          length = strLen / 2;
        }
        let i;
        for (i = 0; i < length; ++i) {
          const parsed = parseInt(string.substr(i * 2, 2), 16);
          if (numberIsNaN(parsed)) return i;
          buf[offset + i] = parsed;
        }
        return i;
      }
      function utf8Write(buf, string, offset, length) {
        return blitBuffer(utf8ToBytes(string, buf.length - offset), buf, offset, length);
      }
      function asciiWrite(buf, string, offset, length) {
        return blitBuffer(asciiToBytes(string), buf, offset, length);
      }
      function base64Write(buf, string, offset, length) {
        return blitBuffer(base64ToBytes(string), buf, offset, length);
      }
      function ucs2Write(buf, string, offset, length) {
        return blitBuffer(utf16leToBytes(string, buf.length - offset), buf, offset, length);
      }
      Buffer3.prototype.write = function write(string, offset, length, encoding) {
        if (offset === void 0) {
          encoding = "utf8";
          length = this.length;
          offset = 0;
        } else if (length === void 0 && typeof offset === "string") {
          encoding = offset;
          length = this.length;
          offset = 0;
        } else if (isFinite(offset)) {
          offset = offset >>> 0;
          if (isFinite(length)) {
            length = length >>> 0;
            if (encoding === void 0) encoding = "utf8";
          } else {
            encoding = length;
            length = void 0;
          }
        } else {
          throw new Error(
            "Buffer.write(string, encoding, offset[, length]) is no longer supported"
          );
        }
        const remaining = this.length - offset;
        if (length === void 0 || length > remaining) length = remaining;
        if (string.length > 0 && (length < 0 || offset < 0) || offset > this.length) {
          throw new RangeError("Attempt to write outside buffer bounds");
        }
        if (!encoding) encoding = "utf8";
        let loweredCase = false;
        for (; ; ) {
          switch (encoding) {
            case "hex":
              return hexWrite(this, string, offset, length);
            case "utf8":
            case "utf-8":
              return utf8Write(this, string, offset, length);
            case "ascii":
            case "latin1":
            case "binary":
              return asciiWrite(this, string, offset, length);
            case "base64":
              return base64Write(this, string, offset, length);
            case "ucs2":
            case "ucs-2":
            case "utf16le":
            case "utf-16le":
              return ucs2Write(this, string, offset, length);
            default:
              if (loweredCase) throw new TypeError("Unknown encoding: " + encoding);
              encoding = ("" + encoding).toLowerCase();
              loweredCase = true;
          }
        }
      };
      Buffer3.prototype.toJSON = function toJSON() {
        return {
          type: "Buffer",
          data: Array.prototype.slice.call(this._arr || this, 0)
        };
      };
      function base64Slice(buf, start, end) {
        if (start === 0 && end === buf.length) {
          return base64.fromByteArray(buf);
        } else {
          return base64.fromByteArray(buf.slice(start, end));
        }
      }
      function utf8Slice(buf, start, end) {
        end = Math.min(buf.length, end);
        const res = [];
        let i = start;
        while (i < end) {
          const firstByte = buf[i];
          let codePoint = null;
          let bytesPerSequence = firstByte > 239 ? 4 : firstByte > 223 ? 3 : firstByte > 191 ? 2 : 1;
          if (i + bytesPerSequence <= end) {
            let secondByte, thirdByte, fourthByte, tempCodePoint;
            switch (bytesPerSequence) {
              case 1:
                if (firstByte < 128) {
                  codePoint = firstByte;
                }
                break;
              case 2:
                secondByte = buf[i + 1];
                if ((secondByte & 192) === 128) {
                  tempCodePoint = (firstByte & 31) << 6 | secondByte & 63;
                  if (tempCodePoint > 127) {
                    codePoint = tempCodePoint;
                  }
                }
                break;
              case 3:
                secondByte = buf[i + 1];
                thirdByte = buf[i + 2];
                if ((secondByte & 192) === 128 && (thirdByte & 192) === 128) {
                  tempCodePoint = (firstByte & 15) << 12 | (secondByte & 63) << 6 | thirdByte & 63;
                  if (tempCodePoint > 2047 && (tempCodePoint < 55296 || tempCodePoint > 57343)) {
                    codePoint = tempCodePoint;
                  }
                }
                break;
              case 4:
                secondByte = buf[i + 1];
                thirdByte = buf[i + 2];
                fourthByte = buf[i + 3];
                if ((secondByte & 192) === 128 && (thirdByte & 192) === 128 && (fourthByte & 192) === 128) {
                  tempCodePoint = (firstByte & 15) << 18 | (secondByte & 63) << 12 | (thirdByte & 63) << 6 | fourthByte & 63;
                  if (tempCodePoint > 65535 && tempCodePoint < 1114112) {
                    codePoint = tempCodePoint;
                  }
                }
            }
          }
          if (codePoint === null) {
            codePoint = 65533;
            bytesPerSequence = 1;
          } else if (codePoint > 65535) {
            codePoint -= 65536;
            res.push(codePoint >>> 10 & 1023 | 55296);
            codePoint = 56320 | codePoint & 1023;
          }
          res.push(codePoint);
          i += bytesPerSequence;
        }
        return decodeCodePointsArray(res);
      }
      var MAX_ARGUMENTS_LENGTH = 4096;
      function decodeCodePointsArray(codePoints) {
        const len = codePoints.length;
        if (len <= MAX_ARGUMENTS_LENGTH) {
          return String.fromCharCode.apply(String, codePoints);
        }
        let res = "";
        let i = 0;
        while (i < len) {
          res += String.fromCharCode.apply(
            String,
            codePoints.slice(i, i += MAX_ARGUMENTS_LENGTH)
          );
        }
        return res;
      }
      function asciiSlice(buf, start, end) {
        let ret = "";
        end = Math.min(buf.length, end);
        for (let i = start; i < end; ++i) {
          ret += String.fromCharCode(buf[i] & 127);
        }
        return ret;
      }
      function latin1Slice(buf, start, end) {
        let ret = "";
        end = Math.min(buf.length, end);
        for (let i = start; i < end; ++i) {
          ret += String.fromCharCode(buf[i]);
        }
        return ret;
      }
      function hexSlice(buf, start, end) {
        const len = buf.length;
        if (!start || start < 0) start = 0;
        if (!end || end < 0 || end > len) end = len;
        let out = "";
        for (let i = start; i < end; ++i) {
          out += hexSliceLookupTable[buf[i]];
        }
        return out;
      }
      function utf16leSlice(buf, start, end) {
        const bytes = buf.slice(start, end);
        let res = "";
        for (let i = 0; i < bytes.length - 1; i += 2) {
          res += String.fromCharCode(bytes[i] + bytes[i + 1] * 256);
        }
        return res;
      }
      Buffer3.prototype.slice = function slice(start, end) {
        const len = this.length;
        start = ~~start;
        end = end === void 0 ? len : ~~end;
        if (start < 0) {
          start += len;
          if (start < 0) start = 0;
        } else if (start > len) {
          start = len;
        }
        if (end < 0) {
          end += len;
          if (end < 0) end = 0;
        } else if (end > len) {
          end = len;
        }
        if (end < start) end = start;
        const newBuf = this.subarray(start, end);
        Object.setPrototypeOf(newBuf, Buffer3.prototype);
        return newBuf;
      };
      function checkOffset(offset, ext, length) {
        if (offset % 1 !== 0 || offset < 0) throw new RangeError("offset is not uint");
        if (offset + ext > length) throw new RangeError("Trying to access beyond buffer length");
      }
      Buffer3.prototype.readUintLE = Buffer3.prototype.readUIntLE = function readUIntLE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) checkOffset(offset, byteLength2, this.length);
        let val = this[offset];
        let mul = 1;
        let i = 0;
        while (++i < byteLength2 && (mul *= 256)) {
          val += this[offset + i] * mul;
        }
        return val;
      };
      Buffer3.prototype.readUintBE = Buffer3.prototype.readUIntBE = function readUIntBE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) {
          checkOffset(offset, byteLength2, this.length);
        }
        let val = this[offset + --byteLength2];
        let mul = 1;
        while (byteLength2 > 0 && (mul *= 256)) {
          val += this[offset + --byteLength2] * mul;
        }
        return val;
      };
      Buffer3.prototype.readUint8 = Buffer3.prototype.readUInt8 = function readUInt8(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 1, this.length);
        return this[offset];
      };
      Buffer3.prototype.readUint16LE = Buffer3.prototype.readUInt16LE = function readUInt16LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        return this[offset] | this[offset + 1] << 8;
      };
      Buffer3.prototype.readUint16BE = Buffer3.prototype.readUInt16BE = function readUInt16BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        return this[offset] << 8 | this[offset + 1];
      };
      Buffer3.prototype.readUint32LE = Buffer3.prototype.readUInt32LE = function readUInt32LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return (this[offset] | this[offset + 1] << 8 | this[offset + 2] << 16) + this[offset + 3] * 16777216;
      };
      Buffer3.prototype.readUint32BE = Buffer3.prototype.readUInt32BE = function readUInt32BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return this[offset] * 16777216 + (this[offset + 1] << 16 | this[offset + 2] << 8 | this[offset + 3]);
      };
      Buffer3.prototype.readBigUInt64LE = defineBigIntMethod(function readBigUInt64LE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const lo = first + this[++offset] * 2 ** 8 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 24;
        const hi = this[++offset] + this[++offset] * 2 ** 8 + this[++offset] * 2 ** 16 + last * 2 ** 24;
        return BigInt(lo) + (BigInt(hi) << BigInt(32));
      });
      Buffer3.prototype.readBigUInt64BE = defineBigIntMethod(function readBigUInt64BE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const hi = first * 2 ** 24 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + this[++offset];
        const lo = this[++offset] * 2 ** 24 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + last;
        return (BigInt(hi) << BigInt(32)) + BigInt(lo);
      });
      Buffer3.prototype.readIntLE = function readIntLE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) checkOffset(offset, byteLength2, this.length);
        let val = this[offset];
        let mul = 1;
        let i = 0;
        while (++i < byteLength2 && (mul *= 256)) {
          val += this[offset + i] * mul;
        }
        mul *= 128;
        if (val >= mul) val -= Math.pow(2, 8 * byteLength2);
        return val;
      };
      Buffer3.prototype.readIntBE = function readIntBE(offset, byteLength2, noAssert) {
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) checkOffset(offset, byteLength2, this.length);
        let i = byteLength2;
        let mul = 1;
        let val = this[offset + --i];
        while (i > 0 && (mul *= 256)) {
          val += this[offset + --i] * mul;
        }
        mul *= 128;
        if (val >= mul) val -= Math.pow(2, 8 * byteLength2);
        return val;
      };
      Buffer3.prototype.readInt8 = function readInt8(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 1, this.length);
        if (!(this[offset] & 128)) return this[offset];
        return (255 - this[offset] + 1) * -1;
      };
      Buffer3.prototype.readInt16LE = function readInt16LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        const val = this[offset] | this[offset + 1] << 8;
        return val & 32768 ? val | 4294901760 : val;
      };
      Buffer3.prototype.readInt16BE = function readInt16BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 2, this.length);
        const val = this[offset + 1] | this[offset] << 8;
        return val & 32768 ? val | 4294901760 : val;
      };
      Buffer3.prototype.readInt32LE = function readInt32LE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return this[offset] | this[offset + 1] << 8 | this[offset + 2] << 16 | this[offset + 3] << 24;
      };
      Buffer3.prototype.readInt32BE = function readInt32BE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return this[offset] << 24 | this[offset + 1] << 16 | this[offset + 2] << 8 | this[offset + 3];
      };
      Buffer3.prototype.readBigInt64LE = defineBigIntMethod(function readBigInt64LE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const val = this[offset + 4] + this[offset + 5] * 2 ** 8 + this[offset + 6] * 2 ** 16 + (last << 24);
        return (BigInt(val) << BigInt(32)) + BigInt(first + this[++offset] * 2 ** 8 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 24);
      });
      Buffer3.prototype.readBigInt64BE = defineBigIntMethod(function readBigInt64BE(offset) {
        offset = offset >>> 0;
        validateNumber(offset, "offset");
        const first = this[offset];
        const last = this[offset + 7];
        if (first === void 0 || last === void 0) {
          boundsError(offset, this.length - 8);
        }
        const val = (first << 24) + // Overflow
        this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + this[++offset];
        return (BigInt(val) << BigInt(32)) + BigInt(this[++offset] * 2 ** 24 + this[++offset] * 2 ** 16 + this[++offset] * 2 ** 8 + last);
      });
      Buffer3.prototype.readFloatLE = function readFloatLE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return ieee754.read(this, offset, true, 23, 4);
      };
      Buffer3.prototype.readFloatBE = function readFloatBE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 4, this.length);
        return ieee754.read(this, offset, false, 23, 4);
      };
      Buffer3.prototype.readDoubleLE = function readDoubleLE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 8, this.length);
        return ieee754.read(this, offset, true, 52, 8);
      };
      Buffer3.prototype.readDoubleBE = function readDoubleBE(offset, noAssert) {
        offset = offset >>> 0;
        if (!noAssert) checkOffset(offset, 8, this.length);
        return ieee754.read(this, offset, false, 52, 8);
      };
      function checkInt(buf, value, offset, ext, max, min) {
        if (!Buffer3.isBuffer(buf)) throw new TypeError('"buffer" argument must be a Buffer instance');
        if (value > max || value < min) throw new RangeError('"value" argument is out of bounds');
        if (offset + ext > buf.length) throw new RangeError("Index out of range");
      }
      Buffer3.prototype.writeUintLE = Buffer3.prototype.writeUIntLE = function writeUIntLE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) {
          const maxBytes = Math.pow(2, 8 * byteLength2) - 1;
          checkInt(this, value, offset, byteLength2, maxBytes, 0);
        }
        let mul = 1;
        let i = 0;
        this[offset] = value & 255;
        while (++i < byteLength2 && (mul *= 256)) {
          this[offset + i] = value / mul & 255;
        }
        return offset + byteLength2;
      };
      Buffer3.prototype.writeUintBE = Buffer3.prototype.writeUIntBE = function writeUIntBE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        byteLength2 = byteLength2 >>> 0;
        if (!noAssert) {
          const maxBytes = Math.pow(2, 8 * byteLength2) - 1;
          checkInt(this, value, offset, byteLength2, maxBytes, 0);
        }
        let i = byteLength2 - 1;
        let mul = 1;
        this[offset + i] = value & 255;
        while (--i >= 0 && (mul *= 256)) {
          this[offset + i] = value / mul & 255;
        }
        return offset + byteLength2;
      };
      Buffer3.prototype.writeUint8 = Buffer3.prototype.writeUInt8 = function writeUInt8(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 1, 255, 0);
        this[offset] = value & 255;
        return offset + 1;
      };
      Buffer3.prototype.writeUint16LE = Buffer3.prototype.writeUInt16LE = function writeUInt16LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 65535, 0);
        this[offset] = value & 255;
        this[offset + 1] = value >>> 8;
        return offset + 2;
      };
      Buffer3.prototype.writeUint16BE = Buffer3.prototype.writeUInt16BE = function writeUInt16BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 65535, 0);
        this[offset] = value >>> 8;
        this[offset + 1] = value & 255;
        return offset + 2;
      };
      Buffer3.prototype.writeUint32LE = Buffer3.prototype.writeUInt32LE = function writeUInt32LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 4294967295, 0);
        this[offset + 3] = value >>> 24;
        this[offset + 2] = value >>> 16;
        this[offset + 1] = value >>> 8;
        this[offset] = value & 255;
        return offset + 4;
      };
      Buffer3.prototype.writeUint32BE = Buffer3.prototype.writeUInt32BE = function writeUInt32BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 4294967295, 0);
        this[offset] = value >>> 24;
        this[offset + 1] = value >>> 16;
        this[offset + 2] = value >>> 8;
        this[offset + 3] = value & 255;
        return offset + 4;
      };
      function wrtBigUInt64LE(buf, value, offset, min, max) {
        checkIntBI(value, min, max, buf, offset, 7);
        let lo = Number(value & BigInt(4294967295));
        buf[offset++] = lo;
        lo = lo >> 8;
        buf[offset++] = lo;
        lo = lo >> 8;
        buf[offset++] = lo;
        lo = lo >> 8;
        buf[offset++] = lo;
        let hi = Number(value >> BigInt(32) & BigInt(4294967295));
        buf[offset++] = hi;
        hi = hi >> 8;
        buf[offset++] = hi;
        hi = hi >> 8;
        buf[offset++] = hi;
        hi = hi >> 8;
        buf[offset++] = hi;
        return offset;
      }
      function wrtBigUInt64BE(buf, value, offset, min, max) {
        checkIntBI(value, min, max, buf, offset, 7);
        let lo = Number(value & BigInt(4294967295));
        buf[offset + 7] = lo;
        lo = lo >> 8;
        buf[offset + 6] = lo;
        lo = lo >> 8;
        buf[offset + 5] = lo;
        lo = lo >> 8;
        buf[offset + 4] = lo;
        let hi = Number(value >> BigInt(32) & BigInt(4294967295));
        buf[offset + 3] = hi;
        hi = hi >> 8;
        buf[offset + 2] = hi;
        hi = hi >> 8;
        buf[offset + 1] = hi;
        hi = hi >> 8;
        buf[offset] = hi;
        return offset + 8;
      }
      Buffer3.prototype.writeBigUInt64LE = defineBigIntMethod(function writeBigUInt64LE(value, offset = 0) {
        return wrtBigUInt64LE(this, value, offset, BigInt(0), BigInt("0xffffffffffffffff"));
      });
      Buffer3.prototype.writeBigUInt64BE = defineBigIntMethod(function writeBigUInt64BE(value, offset = 0) {
        return wrtBigUInt64BE(this, value, offset, BigInt(0), BigInt("0xffffffffffffffff"));
      });
      Buffer3.prototype.writeIntLE = function writeIntLE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          const limit = Math.pow(2, 8 * byteLength2 - 1);
          checkInt(this, value, offset, byteLength2, limit - 1, -limit);
        }
        let i = 0;
        let mul = 1;
        let sub = 0;
        this[offset] = value & 255;
        while (++i < byteLength2 && (mul *= 256)) {
          if (value < 0 && sub === 0 && this[offset + i - 1] !== 0) {
            sub = 1;
          }
          this[offset + i] = (value / mul >> 0) - sub & 255;
        }
        return offset + byteLength2;
      };
      Buffer3.prototype.writeIntBE = function writeIntBE(value, offset, byteLength2, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          const limit = Math.pow(2, 8 * byteLength2 - 1);
          checkInt(this, value, offset, byteLength2, limit - 1, -limit);
        }
        let i = byteLength2 - 1;
        let mul = 1;
        let sub = 0;
        this[offset + i] = value & 255;
        while (--i >= 0 && (mul *= 256)) {
          if (value < 0 && sub === 0 && this[offset + i + 1] !== 0) {
            sub = 1;
          }
          this[offset + i] = (value / mul >> 0) - sub & 255;
        }
        return offset + byteLength2;
      };
      Buffer3.prototype.writeInt8 = function writeInt8(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 1, 127, -128);
        if (value < 0) value = 255 + value + 1;
        this[offset] = value & 255;
        return offset + 1;
      };
      Buffer3.prototype.writeInt16LE = function writeInt16LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 32767, -32768);
        this[offset] = value & 255;
        this[offset + 1] = value >>> 8;
        return offset + 2;
      };
      Buffer3.prototype.writeInt16BE = function writeInt16BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 2, 32767, -32768);
        this[offset] = value >>> 8;
        this[offset + 1] = value & 255;
        return offset + 2;
      };
      Buffer3.prototype.writeInt32LE = function writeInt32LE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 2147483647, -2147483648);
        this[offset] = value & 255;
        this[offset + 1] = value >>> 8;
        this[offset + 2] = value >>> 16;
        this[offset + 3] = value >>> 24;
        return offset + 4;
      };
      Buffer3.prototype.writeInt32BE = function writeInt32BE(value, offset, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) checkInt(this, value, offset, 4, 2147483647, -2147483648);
        if (value < 0) value = 4294967295 + value + 1;
        this[offset] = value >>> 24;
        this[offset + 1] = value >>> 16;
        this[offset + 2] = value >>> 8;
        this[offset + 3] = value & 255;
        return offset + 4;
      };
      Buffer3.prototype.writeBigInt64LE = defineBigIntMethod(function writeBigInt64LE(value, offset = 0) {
        return wrtBigUInt64LE(this, value, offset, -BigInt("0x8000000000000000"), BigInt("0x7fffffffffffffff"));
      });
      Buffer3.prototype.writeBigInt64BE = defineBigIntMethod(function writeBigInt64BE(value, offset = 0) {
        return wrtBigUInt64BE(this, value, offset, -BigInt("0x8000000000000000"), BigInt("0x7fffffffffffffff"));
      });
      function checkIEEE754(buf, value, offset, ext, max, min) {
        if (offset + ext > buf.length) throw new RangeError("Index out of range");
        if (offset < 0) throw new RangeError("Index out of range");
      }
      function writeFloat(buf, value, offset, littleEndian, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          checkIEEE754(buf, value, offset, 4, 34028234663852886e22, -34028234663852886e22);
        }
        ieee754.write(buf, value, offset, littleEndian, 23, 4);
        return offset + 4;
      }
      Buffer3.prototype.writeFloatLE = function writeFloatLE(value, offset, noAssert) {
        return writeFloat(this, value, offset, true, noAssert);
      };
      Buffer3.prototype.writeFloatBE = function writeFloatBE(value, offset, noAssert) {
        return writeFloat(this, value, offset, false, noAssert);
      };
      function writeDouble(buf, value, offset, littleEndian, noAssert) {
        value = +value;
        offset = offset >>> 0;
        if (!noAssert) {
          checkIEEE754(buf, value, offset, 8, 17976931348623157e292, -17976931348623157e292);
        }
        ieee754.write(buf, value, offset, littleEndian, 52, 8);
        return offset + 8;
      }
      Buffer3.prototype.writeDoubleLE = function writeDoubleLE(value, offset, noAssert) {
        return writeDouble(this, value, offset, true, noAssert);
      };
      Buffer3.prototype.writeDoubleBE = function writeDoubleBE(value, offset, noAssert) {
        return writeDouble(this, value, offset, false, noAssert);
      };
      Buffer3.prototype.copy = function copy(target, targetStart, start, end) {
        if (!Buffer3.isBuffer(target)) throw new TypeError("argument should be a Buffer");
        if (!start) start = 0;
        if (!end && end !== 0) end = this.length;
        if (targetStart >= target.length) targetStart = target.length;
        if (!targetStart) targetStart = 0;
        if (end > 0 && end < start) end = start;
        if (end === start) return 0;
        if (target.length === 0 || this.length === 0) return 0;
        if (targetStart < 0) {
          throw new RangeError("targetStart out of bounds");
        }
        if (start < 0 || start >= this.length) throw new RangeError("Index out of range");
        if (end < 0) throw new RangeError("sourceEnd out of bounds");
        if (end > this.length) end = this.length;
        if (target.length - targetStart < end - start) {
          end = target.length - targetStart + start;
        }
        const len = end - start;
        if (this === target && typeof Uint8Array.prototype.copyWithin === "function") {
          this.copyWithin(targetStart, start, end);
        } else {
          Uint8Array.prototype.set.call(
            target,
            this.subarray(start, end),
            targetStart
          );
        }
        return len;
      };
      Buffer3.prototype.fill = function fill(val, start, end, encoding) {
        if (typeof val === "string") {
          if (typeof start === "string") {
            encoding = start;
            start = 0;
            end = this.length;
          } else if (typeof end === "string") {
            encoding = end;
            end = this.length;
          }
          if (encoding !== void 0 && typeof encoding !== "string") {
            throw new TypeError("encoding must be a string");
          }
          if (typeof encoding === "string" && !Buffer3.isEncoding(encoding)) {
            throw new TypeError("Unknown encoding: " + encoding);
          }
          if (val.length === 1) {
            const code = val.charCodeAt(0);
            if (encoding === "utf8" && code < 128 || encoding === "latin1") {
              val = code;
            }
          }
        } else if (typeof val === "number") {
          val = val & 255;
        } else if (typeof val === "boolean") {
          val = Number(val);
        }
        if (start < 0 || this.length < start || this.length < end) {
          throw new RangeError("Out of range index");
        }
        if (end <= start) {
          return this;
        }
        start = start >>> 0;
        end = end === void 0 ? this.length : end >>> 0;
        if (!val) val = 0;
        let i;
        if (typeof val === "number") {
          for (i = start; i < end; ++i) {
            this[i] = val;
          }
        } else {
          const bytes = Buffer3.isBuffer(val) ? val : Buffer3.from(val, encoding);
          const len = bytes.length;
          if (len === 0) {
            throw new TypeError('The value "' + val + '" is invalid for argument "value"');
          }
          for (i = 0; i < end - start; ++i) {
            this[i + start] = bytes[i % len];
          }
        }
        return this;
      };
      var errors = {};
      function E(sym, getMessage, Base) {
        errors[sym] = class NodeError extends Base {
          constructor() {
            super();
            Object.defineProperty(this, "message", {
              value: getMessage.apply(this, arguments),
              writable: true,
              configurable: true
            });
            this.name = `${this.name} [${sym}]`;
            this.stack;
            delete this.name;
          }
          get code() {
            return sym;
          }
          set code(value) {
            Object.defineProperty(this, "code", {
              configurable: true,
              enumerable: true,
              value,
              writable: true
            });
          }
          toString() {
            return `${this.name} [${sym}]: ${this.message}`;
          }
        };
      }
      E(
        "ERR_BUFFER_OUT_OF_BOUNDS",
        function(name) {
          if (name) {
            return `${name} is outside of buffer bounds`;
          }
          return "Attempt to access memory outside buffer bounds";
        },
        RangeError
      );
      E(
        "ERR_INVALID_ARG_TYPE",
        function(name, actual) {
          return `The "${name}" argument must be of type number. Received type ${typeof actual}`;
        },
        TypeError
      );
      E(
        "ERR_OUT_OF_RANGE",
        function(str, range, input) {
          let msg = `The value of "${str}" is out of range.`;
          let received = input;
          if (Number.isInteger(input) && Math.abs(input) > 2 ** 32) {
            received = addNumericalSeparator(String(input));
          } else if (typeof input === "bigint") {
            received = String(input);
            if (input > BigInt(2) ** BigInt(32) || input < -(BigInt(2) ** BigInt(32))) {
              received = addNumericalSeparator(received);
            }
            received += "n";
          }
          msg += ` It must be ${range}. Received ${received}`;
          return msg;
        },
        RangeError
      );
      function addNumericalSeparator(val) {
        let res = "";
        let i = val.length;
        const start = val[0] === "-" ? 1 : 0;
        for (; i >= start + 4; i -= 3) {
          res = `_${val.slice(i - 3, i)}${res}`;
        }
        return `${val.slice(0, i)}${res}`;
      }
      function checkBounds(buf, offset, byteLength2) {
        validateNumber(offset, "offset");
        if (buf[offset] === void 0 || buf[offset + byteLength2] === void 0) {
          boundsError(offset, buf.length - (byteLength2 + 1));
        }
      }
      function checkIntBI(value, min, max, buf, offset, byteLength2) {
        if (value > max || value < min) {
          const n = typeof min === "bigint" ? "n" : "";
          let range;
          if (byteLength2 > 3) {
            if (min === 0 || min === BigInt(0)) {
              range = `>= 0${n} and < 2${n} ** ${(byteLength2 + 1) * 8}${n}`;
            } else {
              range = `>= -(2${n} ** ${(byteLength2 + 1) * 8 - 1}${n}) and < 2 ** ${(byteLength2 + 1) * 8 - 1}${n}`;
            }
          } else {
            range = `>= ${min}${n} and <= ${max}${n}`;
          }
          throw new errors.ERR_OUT_OF_RANGE("value", range, value);
        }
        checkBounds(buf, offset, byteLength2);
      }
      function validateNumber(value, name) {
        if (typeof value !== "number") {
          throw new errors.ERR_INVALID_ARG_TYPE(name, "number", value);
        }
      }
      function boundsError(value, length, type) {
        if (Math.floor(value) !== value) {
          validateNumber(value, type);
          throw new errors.ERR_OUT_OF_RANGE(type || "offset", "an integer", value);
        }
        if (length < 0) {
          throw new errors.ERR_BUFFER_OUT_OF_BOUNDS();
        }
        throw new errors.ERR_OUT_OF_RANGE(
          type || "offset",
          `>= ${type ? 1 : 0} and <= ${length}`,
          value
        );
      }
      var INVALID_BASE64_RE = /[^+/0-9A-Za-z-_]/g;
      function base64clean(str) {
        str = str.split("=")[0];
        str = str.trim().replace(INVALID_BASE64_RE, "");
        if (str.length < 2) return "";
        while (str.length % 4 !== 0) {
          str = str + "=";
        }
        return str;
      }
      function utf8ToBytes(string, units) {
        units = units || Infinity;
        let codePoint;
        const length = string.length;
        let leadSurrogate = null;
        const bytes = [];
        for (let i = 0; i < length; ++i) {
          codePoint = string.charCodeAt(i);
          if (codePoint > 55295 && codePoint < 57344) {
            if (!leadSurrogate) {
              if (codePoint > 56319) {
                if ((units -= 3) > -1) bytes.push(239, 191, 189);
                continue;
              } else if (i + 1 === length) {
                if ((units -= 3) > -1) bytes.push(239, 191, 189);
                continue;
              }
              leadSurrogate = codePoint;
              continue;
            }
            if (codePoint < 56320) {
              if ((units -= 3) > -1) bytes.push(239, 191, 189);
              leadSurrogate = codePoint;
              continue;
            }
            codePoint = (leadSurrogate - 55296 << 10 | codePoint - 56320) + 65536;
          } else if (leadSurrogate) {
            if ((units -= 3) > -1) bytes.push(239, 191, 189);
          }
          leadSurrogate = null;
          if (codePoint < 128) {
            if ((units -= 1) < 0) break;
            bytes.push(codePoint);
          } else if (codePoint < 2048) {
            if ((units -= 2) < 0) break;
            bytes.push(
              codePoint >> 6 | 192,
              codePoint & 63 | 128
            );
          } else if (codePoint < 65536) {
            if ((units -= 3) < 0) break;
            bytes.push(
              codePoint >> 12 | 224,
              codePoint >> 6 & 63 | 128,
              codePoint & 63 | 128
            );
          } else if (codePoint < 1114112) {
            if ((units -= 4) < 0) break;
            bytes.push(
              codePoint >> 18 | 240,
              codePoint >> 12 & 63 | 128,
              codePoint >> 6 & 63 | 128,
              codePoint & 63 | 128
            );
          } else {
            throw new Error("Invalid code point");
          }
        }
        return bytes;
      }
      function asciiToBytes(str) {
        const byteArray = [];
        for (let i = 0; i < str.length; ++i) {
          byteArray.push(str.charCodeAt(i) & 255);
        }
        return byteArray;
      }
      function utf16leToBytes(str, units) {
        let c, hi, lo;
        const byteArray = [];
        for (let i = 0; i < str.length; ++i) {
          if ((units -= 2) < 0) break;
          c = str.charCodeAt(i);
          hi = c >> 8;
          lo = c % 256;
          byteArray.push(lo);
          byteArray.push(hi);
        }
        return byteArray;
      }
      function base64ToBytes(str) {
        return base64.toByteArray(base64clean(str));
      }
      function blitBuffer(src, dst, offset, length) {
        let i;
        for (i = 0; i < length; ++i) {
          if (i + offset >= dst.length || i >= src.length) break;
          dst[i + offset] = src[i];
        }
        return i;
      }
      function isInstance(obj, type) {
        return obj instanceof type || obj != null && obj.constructor != null && obj.constructor.name != null && obj.constructor.name === type.name;
      }
      function numberIsNaN(obj) {
        return obj !== obj;
      }
      var hexSliceLookupTable = (function() {
        const alphabet = "0123456789abcdef";
        const table = new Array(256);
        for (let i = 0; i < 16; ++i) {
          const i16 = i * 16;
          for (let j = 0; j < 16; ++j) {
            table[i16 + j] = alphabet[i] + alphabet[j];
          }
        }
        return table;
      })();
      function defineBigIntMethod(fn) {
        return typeof BigInt === "undefined" ? BufferBigIntNotDefined : fn;
      }
      function BufferBigIntNotDefined() {
        throw new Error("BigInt not supported");
      }
    }
  });

  // node_modules/intel-hex/index.js
  var require_intel_hex = __commonJS({
    "node_modules/intel-hex/index.js"(exports) {
      var DATA = 0;
      var END_OF_FILE = 1;
      var EXT_SEGMENT_ADDR = 2;
      var START_SEGMENT_ADDR = 3;
      var EXT_LINEAR_ADDR = 4;
      var START_LINEAR_ADDR = 5;
      var EMPTY_VALUE = 255;
      exports.parse = function parseIntelHex(data, bufferSize, addressOffset) {
        if (data instanceof Buffer)
          data = data.toString("ascii");
        var buf = Buffer.alloc(bufferSize || 8192), bufLength = 0, highAddress = 0, startSegmentAddress = null, startLinearAddress = null, addressOffset = addressOffset || 0, lineNum = 0, pos = 0;
        const SMALLEST_LINE = 11;
        while (pos + SMALLEST_LINE <= data.length) {
          if (data.charAt(pos++) != ":")
            throw new Error("Line " + (lineNum + 1) + " does not start with a colon (:).");
          else
            lineNum++;
          var dataLength = parseInt(data.substr(pos, 2), 16);
          pos += 2;
          var lowAddress = parseInt(data.substr(pos, 4), 16);
          pos += 4;
          var recordType = parseInt(data.substr(pos, 2), 16);
          pos += 2;
          var dataField = data.substr(pos, dataLength * 2), dataFieldBuf = Buffer.from(dataField, "hex");
          pos += dataLength * 2;
          var checksum = parseInt(data.substr(pos, 2), 16);
          pos += 2;
          var calcChecksum = dataLength + (lowAddress >> 8) + lowAddress + recordType & 255;
          for (var i = 0; i < dataLength; i++)
            calcChecksum = calcChecksum + dataFieldBuf[i] & 255;
          calcChecksum = 256 - calcChecksum & 255;
          if (checksum != calcChecksum)
            throw new Error("Invalid checksum on line " + lineNum + ": got " + checksum + ", but expected " + calcChecksum);
          switch (recordType) {
            case DATA:
              var absoluteAddress = highAddress + lowAddress - addressOffset;
              if (absoluteAddress + dataLength >= buf.length) {
                var tmp = Buffer.alloc((absoluteAddress + dataLength) * 2);
                buf.copy(tmp, 0, 0, bufLength);
                buf = tmp;
              }
              if (absoluteAddress > bufLength)
                buf.fill(EMPTY_VALUE, bufLength, absoluteAddress);
              dataFieldBuf.copy(buf, absoluteAddress);
              bufLength = Math.max(bufLength, absoluteAddress + dataLength);
              if (bufLength >= bufferSize) {
                return {
                  "data": buf.slice(0, bufLength),
                  "startSegmentAddress": startSegmentAddress,
                  "startLinearAddress": startLinearAddress
                };
              }
              break;
            case END_OF_FILE:
              if (dataLength != 0)
                throw new Error("Invalid EOF record on line " + lineNum + ".");
              return {
                "data": buf.slice(0, bufLength),
                "startSegmentAddress": startSegmentAddress,
                "startLinearAddress": startLinearAddress
              };
              break;
            case EXT_SEGMENT_ADDR:
              if (dataLength != 2 || lowAddress != 0)
                throw new Error("Invalid extended segment address record on line " + lineNum + ".");
              highAddress = parseInt(dataField, 16) << 4;
              break;
            case START_SEGMENT_ADDR:
              if (dataLength != 4 || lowAddress != 0)
                throw new Error("Invalid start segment address record on line " + lineNum + ".");
              startSegmentAddress = parseInt(dataField, 16);
              break;
            case EXT_LINEAR_ADDR:
              if (dataLength != 2 || lowAddress != 0)
                throw new Error("Invalid extended linear address record on line " + lineNum + ".");
              highAddress = parseInt(dataField, 16) << 16;
              break;
            case START_LINEAR_ADDR:
              if (dataLength != 4 || lowAddress != 0)
                throw new Error("Invalid start linear address record on line " + lineNum + ".");
              startLinearAddress = parseInt(dataField, 16);
              break;
            default:
              throw new Error("Invalid record type (" + recordType + ") on line " + lineNum);
              break;
          }
          if (data.charAt(pos) == "\r")
            pos++;
          if (data.charAt(pos) == "\n")
            pos++;
        }
        throw new Error("Unexpected end of input: missing or invalid EOF record.");
      };
    }
  });

  // bundle.js
  var import_buffer = __toESM(require_buffer());

  // node_modules/avr8js/dist/esm/index.js
  var esm_exports = {};
  __export(esm_exports, {
    ADCMuxInputType: () => ADCMuxInputType,
    ADCReference: () => ADCReference,
    ATtinyTimer1: () => ATtinyTimer1,
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
    attinyTimer1Config: () => attinyTimer1Config,
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
    // 1.8ms at 16MHz
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
    // External clock - see ExternalClockMode
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
    // Unused
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

  // node_modules/avr8js/dist/esm/peripherals/timer-attiny.js
  var CTC1 = 1 << 7;
  var PWM1A = 1 << 6;
  var CS_MASK = 15;
  var PWM1B_BIT = 1 << 6;
  var FOC1B = 1 << 3;
  var FOC1A = 1 << 2;
  var PSR1 = 1 << 1;
  var attinyTimer1Config = {
    TCCR1: 80,
    GTCCR: 76,
    TCNT1: 79,
    OCR1A: 78,
    OCR1B: 75,
    OCR1C: 77,
    TIFR: 88,
    TIMSK: 89,
    ovfInterrupt: 4,
    compAInterrupt: 3,
    compBInterrupt: 9,
    TOV1: 1 << 2,
    OCF1A: 1 << 6,
    OCF1B: 1 << 5,
    TOIE1: 1 << 2,
    OCIE1A: 1 << 6,
    OCIE1B: 1 << 5,
    compPortB: 56,
    compPinA: 1,
    // PB1
    compPinB: 4,
    // PB4
    dividers: {
      0: 0,
      1: 1,
      2: 2,
      3: 4,
      4: 8,
      5: 16,
      6: 32,
      7: 64,
      8: 128,
      9: 256,
      10: 512,
      11: 1024,
      12: 2048,
      13: 4096,
      14: 8192,
      15: 16384
    }
  };
  var ATtinyTimer1 = class {
    constructor(cpu, config) {
      this.cpu = cpu;
      this.config = config;
      this.lastCycle = 0;
      this.tcnt = 0;
      this.tcntNext = 0;
      this.tcntUpdated = false;
      this.ocrA = 0;
      this.ocrB = 0;
      this.ocrC = 0;
      this.divider = 0;
      this.updateDivider = false;
      this.countingUp = true;
      this.OVF = {
        address: this.config.ovfInterrupt,
        flagRegister: this.config.TIFR,
        flagMask: this.config.TOV1,
        enableRegister: this.config.TIMSK,
        enableMask: this.config.TOIE1
      };
      this.OCFA = {
        address: this.config.compAInterrupt,
        flagRegister: this.config.TIFR,
        flagMask: this.config.OCF1A,
        enableRegister: this.config.TIMSK,
        enableMask: this.config.OCIE1A
      };
      this.OCFB = {
        address: this.config.compBInterrupt,
        flagRegister: this.config.TIFR,
        flagMask: this.config.OCF1B,
        enableRegister: this.config.TIMSK,
        enableMask: this.config.OCIE1B
      };
      this.count = (reschedule = true) => {
        var _a;
        const { divider, lastCycle, cpu: cpu2 } = this;
        const { cycles } = cpu2;
        const delta = cycles - lastCycle;
        if (divider && delta >= divider) {
          const counterDelta = Math.floor(delta / divider);
          this.lastCycle += counterDelta * divider;
          const val = this.tcnt;
          const top = this.TOP;
          const phasePwm = (this.pwmA || this.pwmB) && !this.ctcMode;
          const newVal = phasePwm ? this.phasePwmCount(val, counterDelta) : (val + counterDelta) % (top + 1);
          const overflow = val + counterDelta > top;
          if (!this.tcntUpdated) {
            this.tcnt = newVal;
            if (!phasePwm) {
              this.timerUpdated(newVal, val);
            }
          }
          if (!phasePwm && overflow) {
            cpu2.setInterruptFlag(this.OVF);
          }
        }
        if (this.tcntUpdated) {
          this.tcnt = this.tcntNext;
          this.tcntUpdated = false;
        }
        if (this.updateDivider) {
          const cs = this.CS;
          const newDivider = (_a = this.config.dividers[cs]) !== null && _a !== void 0 ? _a : 0;
          this.lastCycle = newDivider ? this.cpu.cycles : 0;
          this.updateDivider = false;
          this.divider = newDivider;
          if (newDivider) {
            cpu2.addClockEvent(this.count, this.lastCycle + newDivider - cpu2.cycles);
          }
          return;
        }
        if (reschedule && divider) {
          cpu2.addClockEvent(this.count, this.lastCycle + divider - cpu2.cycles);
        }
      };
      const { TCCR1, GTCCR, TCNT1, OCR1A, OCR1B, OCR1C, TIFR, TIMSK } = config;
      cpu.readHooks[TCNT1] = () => {
        this.count(false);
        return cpu.data[TCNT1] = this.tcnt & 255;
      };
      cpu.writeHooks[TCNT1] = (value) => {
        this.tcntNext = value;
        this.countingUp = true;
        this.tcntUpdated = true;
        cpu.updateClockEvent(this.count, 0);
        if (this.divider) {
          this.timerUpdated(this.tcntNext, this.tcntNext);
        }
      };
      cpu.writeHooks[OCR1A] = (value) => {
        this.ocrA = value;
      };
      cpu.writeHooks[OCR1B] = (value) => {
        this.ocrB = value;
      };
      cpu.writeHooks[OCR1C] = (value) => {
        this.ocrC = value;
      };
      cpu.writeHooks[TCCR1] = (value) => {
        cpu.data[TCCR1] = value;
        this.updateDivider = true;
        cpu.clearClockEvent(this.count);
        cpu.addClockEvent(this.count, 0);
        this.updateCompConfig();
        return true;
      };
      const prevGtccrHook = cpu.writeHooks[GTCCR];
      cpu.writeHooks[GTCCR] = (value, oldValue, addr, mask) => {
        if (value & FOC1A) {
          this.forceCompare("A");
        }
        if (value & FOC1B) {
          this.forceCompare("B");
        }
        if (value & PSR1) {
          this.lastCycle = this.cpu.cycles;
        }
        value &= ~(FOC1A | FOC1B | PSR1);
        if (prevGtccrHook) {
          prevGtccrHook(value, oldValue, addr, mask);
        } else {
          cpu.data[GTCCR] = value;
        }
        this.updateCompConfig();
        return true;
      };
      const prevTifrHook = cpu.writeHooks[TIFR];
      cpu.writeHooks[TIFR] = (value, oldValue, addr, mask) => {
        if (prevTifrHook) {
          prevTifrHook(value, oldValue, addr, mask);
        } else {
          cpu.data[TIFR] = value;
        }
        cpu.clearInterruptByFlag(this.OVF, value);
        cpu.clearInterruptByFlag(this.OCFA, value);
        cpu.clearInterruptByFlag(this.OCFB, value);
        return true;
      };
      const prevTimskHook = cpu.writeHooks[TIMSK];
      cpu.writeHooks[TIMSK] = (value, oldValue, addr, mask) => {
        if (prevTimskHook) {
          prevTimskHook(value, oldValue, addr, mask);
        }
        cpu.updateInterruptEnable(this.OVF, value);
        cpu.updateInterruptEnable(this.OCFA, value);
        cpu.updateInterruptEnable(this.OCFB, value);
      };
    }
    get tccr1() {
      return this.cpu.data[this.config.TCCR1];
    }
    get gtccr() {
      return this.cpu.data[this.config.GTCCR];
    }
    get CS() {
      return this.tccr1 & CS_MASK;
    }
    get ctcMode() {
      return !!(this.tccr1 & CTC1);
    }
    get pwmA() {
      return !!(this.tccr1 & PWM1A);
    }
    get pwmB() {
      return !!(this.gtccr & PWM1B_BIT);
    }
    get comA() {
      return this.tccr1 >> 4 & 3;
    }
    get comB() {
      return this.gtccr >> 4 & 3;
    }
    /** TOP = OCR1C in CTC/PWM modes, 0xFF in Normal mode */
    get TOP() {
      if (this.ctcMode || this.pwmA || this.pwmB) {
        return this.ocrC;
      }
      return 255;
    }
    phasePwmCount(value, delta) {
      const top = this.TOP;
      while (delta > 0) {
        if (this.countingUp) {
          value++;
          if (value >= top) {
            value = top;
            this.countingUp = false;
          }
        } else {
          value--;
          if (value <= 0) {
            value = 0;
            this.countingUp = true;
            this.cpu.setInterruptFlag(this.OVF);
          }
        }
        if (!this.tcntUpdated) {
          if (value === this.ocrA) {
            this.cpu.setInterruptFlag(this.OCFA);
            this.updateCompPinPwm("A");
          }
          if (value === this.ocrB) {
            this.cpu.setInterruptFlag(this.OCFB);
            this.updateCompPinPwm("B");
          }
        }
        delta--;
      }
      return value & 255;
    }
    timerUpdated(value, prevValue) {
      const { ocrA, ocrB } = this;
      const overflow = prevValue > value;
      if ((prevValue < ocrA || overflow) && value >= ocrA || prevValue < ocrA && overflow) {
        this.cpu.setInterruptFlag(this.OCFA);
        if (this.comA && !this.pwmA) {
          this.updateCompPinNonPwm("A");
        }
      }
      if ((prevValue < ocrB || overflow) && value >= ocrB || prevValue < ocrB && overflow) {
        this.cpu.setInterruptFlag(this.OCFB);
        if (this.comB && !this.pwmB) {
          this.updateCompPinNonPwm("B");
        }
      }
    }
    forceCompare(channel) {
      if (channel === "A" && !this.pwmA && this.comA) {
        this.updateCompPinNonPwm("A");
      } else if (channel === "B" && !this.pwmB && this.comB) {
        this.updateCompPinNonPwm("B");
      }
    }
    updateCompPinNonPwm(channel) {
      var _a;
      const com = channel === "A" ? this.comA : this.comB;
      const pin = channel === "A" ? this.config.compPinA : this.config.compPinB;
      let mode;
      switch (com) {
        case 1:
          mode = PinOverrideMode.Toggle;
          break;
        case 2:
          mode = PinOverrideMode.Clear;
          break;
        case 3:
          mode = PinOverrideMode.Set;
          break;
        default:
          return;
      }
      (_a = this.cpu.gpioByPort[this.config.compPortB]) === null || _a === void 0 ? void 0 : _a.timerOverridePin(pin, mode);
    }
    updateCompPinPwm(channel) {
      var _a;
      const com = channel === "A" ? this.comA : this.comB;
      const pin = channel === "A" ? this.config.compPinA : this.config.compPinB;
      const invertingMode = com === 3;
      const isSet = this.countingUp === invertingMode;
      let mode;
      switch (com) {
        case 1:
          mode = PinOverrideMode.Toggle;
          break;
        case 2:
        case 3:
          mode = isSet ? PinOverrideMode.Set : PinOverrideMode.Clear;
          break;
        default:
          return;
      }
      (_a = this.cpu.gpioByPort[this.config.compPortB]) === null || _a === void 0 ? void 0 : _a.timerOverridePin(pin, mode);
    }
    updateCompConfig() {
      const port = this.cpu.gpioByPort[this.config.compPortB];
      if (!port)
        return;
      port.timerOverridePin(this.config.compPinA, this.comA ? PinOverrideMode.Enable : PinOverrideMode.None);
      port.timerOverridePin(this.config.compPinB, this.comB ? PinOverrideMode.Enable : PinOverrideMode.None);
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

  // bundle.js
  var import_intel_hex = __toESM(require_intel_hex());
  window.Buffer = import_buffer.Buffer;
  window.AVR8JS = esm_exports;
  window.AVR8JS.parseHex = function(hex) {
    return (0, import_intel_hex.parse)(hex).data;
  };
})();
/*! Bundled license information:

ieee754/index.js:
  (*! ieee754. BSD-3-Clause License. Feross Aboukhadijeh <https://feross.org/opensource> *)

buffer/index.js:
  (*!
   * The buffer module from node.js, for the browser.
   *
   * @author   Feross Aboukhadijeh <https://feross.org>
   * @license  MIT
   *)
*/
