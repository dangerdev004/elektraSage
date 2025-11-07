import React, { useRef, useEffect, useState, useCallback } from "react";

function CircuitCanvas({ showGrid, theme, smallGrid, elements = [], onMouseDown, onMouseMove, onMouseUp }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const lastTimeRef = useRef(0);

  const gridSize = smallGrid ? 10 : 20;
  // eslint-disable-next-line no-unused-vars
  const [transform, setTransform] = useState([0, 0, 1]);

  // --- DRAW FUNCTION ---
  // Wrapped in useCallback so we can access latest props/state without stale closures,
  // though for 'elements' array we rely on its mutable nature.
  const draw = useCallback((ctx, canvas, dt) => {
      const dpr = window.devicePixelRatio || 1;
      const width = canvas.width / dpr;
      const height = canvas.height / dpr;

      ctx.save();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Clear background
      ctx.fillStyle = theme === "dark" ? "#000000" : "#ffffff";
      ctx.fillRect(0, 0, width, height);

      // Draw Grid
      if (showGrid) {
        ctx.strokeStyle = theme === "dark" ? "#555" : "#ccc";
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        for (let x = 0; x < width; x += gridSize) {
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
        }
        for (let y = 0; y < height; y += gridSize) {
          ctx.moveTo(0, y);
          ctx.lineTo(width, y);
        }
        ctx.stroke();
      }

      // Draw Elements
      // We trust that 'elements' is mutable and being updated by App.js sim loop
      if (elements) {
         // 1. Standard Draw Pass
         elements.forEach((elm) => {
            if (elm?.draw) elm.draw(ctx);
         });
         
         // 2. Current Dot Pass
         // dt is in milliseconds. Adjust scaler to taste for dot speed.
         const curScale = 0.5 * (1000 / 60);
         
         elements.forEach((elm) => {
             if (elm?.drawDots) {
                 elm.updateDotCount(curScale);
                 elm.drawDots(ctx);
             }
         });
      }

      ctx.restore();
  }, [showGrid, theme, gridSize, elements]); // Dependencies for draw configuration

  // --- MAIN RENDER LOOP ---
  useEffect(() => {
      const render = (time) => {
          // Calculate delta time for smooth animation regardless of FPS
          const dt = time - lastTimeRef.current;
          lastTimeRef.current = time;
          
          const canvas = canvasRef.current;
          if (canvas) {
               const ctx = canvas.getContext("2d");
               draw(ctx, canvas, dt);
          }
          
          animationRef.current = requestAnimationFrame(render);
      };

      // Start the loop
      animationRef.current = requestAnimationFrame(render);

      return () => {
          if (animationRef.current) {
              cancelAnimationFrame(animationRef.current);
          }
      };
  }, [draw]); // Re-start loop if draw function (and its dependencies) change

  // --- RESIZE HANDLING ---
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resizeCanvas = () => {
      const rect = canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      
      if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
          canvas.width = rect.width * dpr;
          canvas.height = rect.height * dpr;
          canvas.style.width = rect.width + "px";
          canvas.style.height = rect.height + "px";
      }
    };

    const ro = new ResizeObserver(resizeCanvas);
    ro.observe(canvas.parentElement);
    resizeCanvas(); // Initial size

    return () => ro.disconnect();
  }, []);

  // --- EVENT COORDINATE NORMALIZER ---
  const getCanvasCoordinates = (event) => {
      const rect = canvasRef.current.getBoundingClientRect();
      return { 
          x: event.clientX - rect.left, 
          y: event.clientY - rect.top 
      };
  };

  return (
    <canvas 
       ref={canvasRef} 
       style={{ display: "block" }}
       onMouseDown={(e) => {
           const {x, y} = getCanvasCoordinates(e);
           onMouseDown(x, y);
       }}
       onMouseMove={(e) => {
           const {x, y} = getCanvasCoordinates(e);
           onMouseMove(x, y);
       }}
       onMouseUp={(e) => {
           onMouseUp();
       }}
    />
  );
}

export default CircuitCanvas;