import React, { useRef, useEffect, useState } from "react";

function CircuitCanvas({ showGrid, theme, smallGrid, elements = [] }) {
  const canvasRef = useRef(null);
  const gridSize = smallGrid ? 10 : 20;

  const [transform, setTransform] = useState([0, 0, 1]);
  // eslint-disable-next-line no-unused-vars
  const [circuitArea, setCircuitArea] = useState({ x: 0, y: 0, width: 0, height: 0 });
  // eslint-disable-next-line no-unused-vars
  const [mouseMode, setMouseMode] = useState("SELECT");
  // eslint-disable-next-line no-unused-vars
  const [mouseDragging, setMouseDragging] = useState(false);
  // eslint-disable-next-line no-unused-vars
  const [dragElm, setDragElm] = useState(null);
  // eslint-disable-next-line no-unused-vars
  const [initDragX, setInitDragX] = useState(0);
  // eslint-disable-next-line no-unused-vars
  const [initDragY, setInitDragY] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    // Set context properties
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    function resizeCanvas() {
      const rect = canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;

      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";

      ctx.scale(dpr, dpr);

      setCircuitArea({ x: 0, y: 0, width: rect.width, height: rect.height });
      draw();
    }

    function draw() {
      const dpr = window.devicePixelRatio || 1;
      ctx.save();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      ctx.fillStyle = theme === "dark" ? "#000000" : "#ffffff";
      ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr);

      if (showGrid) {
        ctx.strokeStyle = theme === "dark" ? "#555" : "#ccc";
        ctx.lineWidth = 0.5;

        for (let x = 0; x < canvas.width / dpr; x += gridSize) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, canvas.height / dpr);
          ctx.stroke();
        }
        for (let y = 0; y < canvas.height / dpr; y += gridSize) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(canvas.width / dpr, y);
          ctx.stroke();
        }
      }

      // Safe loop over elements
      (elements || []).forEach((elm) => {
        if (elm?.draw) {
          elm.draw(ctx);
        } else if (elm?.x !== undefined && elm?.y !== undefined) {
          // Fallback for simple dots (from clicks)
          ctx.fillStyle = theme === "dark" ? "yellow" : "red";
          ctx.beginPath();
          ctx.arc(elm.x, elm.y, 4, 0, 2 * Math.PI);
          ctx.fill();
        }
      });

      ctx.restore();
    }

    function handleClick(event) {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const snappedX = Math.round(x / gridSize) * gridSize;
      const snappedY = Math.round(y / gridSize) * gridSize;

    }

    const ro = new ResizeObserver(resizeCanvas);
    ro.observe(canvas.parentElement);
    window.addEventListener("resize", resizeCanvas);
    canvas.addEventListener("click", handleClick);

    resizeCanvas();

    return () => {
      ro.disconnect();
      window.removeEventListener("resize", resizeCanvas);
      canvas.removeEventListener("click", handleClick);
    };
  }, [showGrid, theme, smallGrid, gridSize, elements, transform]);

  return <canvas ref={canvasRef} style={{ display: "block" }} />;
}

export default CircuitCanvas;