// // import React from "react";

// // function CircuitCanvas({ showGrid, theme, smallGrid, dots, onAddDot }) {
// //   const canvasRef = React.useRef(null);
// //   const gridSize = smallGrid ? 10 : 20;

// //   React.useEffect(() => {
// //     const canvas = canvasRef.current;
// //     const ctx = canvas.getContext("2d");

// //     function resizeCanvas() {
// //       canvas.parent = canvas.parentElement;
// //       const rect = canvas.parentElement.getBoundingClientRect();
// //       canvas.width = rect.width;
// //       canvas.height = rect.height;
// //       draw();
// //     }

// //     function draw() {
// //       ctx.fillStyle = theme === "dark" ? "#000000" : "#ffffff";
// //       ctx.fillRect(0, 0, canvas.width, canvas.height);

// //       if (showGrid) {
// //         ctx.strokeStyle = theme === "dark" ? "#555" : "#ccc";
// //         ctx.lineWidth = 0.5;

// //         for (let x = 0; x < canvas.width; x += gridSize) {
// //           ctx.beginPath();
// //           ctx.moveTo(x, 0);
// //           ctx.lineTo(x, canvas.height);
// //           ctx.stroke();
// //         }
// //         for (let y = 0; y < canvas.height; y += gridSize) {
// //           ctx.beginPath();
// //           ctx.moveTo(0, y);
// //           ctx.lineTo(canvas.width, y);
// //           ctx.stroke();
// //         }
// //       }

// //       dots.forEach((dot) => {
// //         ctx.fillStyle = theme === "dark" ? "yellow" : "red";
// //         ctx.beginPath();
// //         ctx.arc(dot.x, dot.y, 4, 0, 2 * Math.PI);
// //         ctx.fill();
// //       });
// //     }

// //     function handleClick(event) {
// //       const rect = canvas.getBoundingClientRect();
// //       const x = event.clientX - rect.left;
// //       const y = event.clientY - rect.top;

// //       // Snap to grid
// //       const snappedX = Math.round(x / gridSize) * gridSize;
// //       const snappedY = Math.round(y / gridSize) * gridSize;

// //       console.log("Clicked:", x, y, " Snapped:", snappedX, snappedY);

// //       // Example: draw a dot at the snapped location
// //       onAddDot({ x: snappedX, y: snappedY });
// //     }

// //     const ro = new ResizeObserver(resizeCanvas);
// //     ro.observe(canvas.parentElement);
// //     window.addEventListener("resize", resizeCanvas);
// //     canvas.addEventListener("click", handleClick);

// //     resizeCanvas();

// //     return () => {
// //       ro.disconnect();
// //       window.removeEventListener("resize", resizeCanvas);
// //       canvas.removeEventListener("click", handleClick);
// //     };
// //   }, [showGrid, theme, smallGrid, gridSize, dots, onAddDot]);

// //   return <canvas ref={canvasRef} style={{ display: "block" }} />;
// // }

// // export default CircuitCanvas;

// import React from "react";

// function CircuitCanvas({ showGrid, theme, smallGrid, dots, onAddDot }) {
//   const canvasRef = React.useRef(null);
//   const gridSize = smallGrid ? 10 : 20;
  
//   const [transform, setTransform] = React.useState([0, 0, 1]);
//   const [circuitArea, setCircuitArea] = React.useState({ x: 0, y: 0, width: 0, height: 0 });
//   const [mouseMode, setMouseMode] = React.useState("SELECT");
//   const [mouseDragging, setMouseDragging] = React.useState(false);
//   const [dragElm, setDragElm] = React.useState(null);
//   const [initDragX, setInitDragX] = React.useState(0);
//   const [initDragY, setInitDragY] = React.useState(0);

//   // Transform functions
//   const transformX = (x) => (x - transform[0]) * transform[2];
//   const transformY = (y) => (y - transform[1]) * transform[2];
//   const inverseTransformX = (x) => x / transform[2] + transform[0];
//   const inverseTransformY = (y) => y / transform[2] + transform[1];

//   React.useEffect(() => {
//     const canvas = canvasRef.current;
//     const ctx = canvas.getContext("2d");
    
//     // Set context properties
//     ctx.lineCap = "round";
//     ctx.lineJoin = "round";

//     function resizeCanvas() {
//       const rect = canvas.parentElement.getBoundingClientRect();
//       const dpr = window.devicePixelRatio || 1;
      
//       canvas.width = rect.width * dpr;
//       canvas.height = rect.height * dpr;
//       canvas.style.width = rect.width + 'px';
//       canvas.style.height = rect.height + 'px';
      
//       ctx.scale(dpr, dpr);
      
//       setCircuitArea({ x: 0, y: 0, width: rect.width, height: rect.height });
//       draw();
//     }

//     function draw() {
//       const dpr = window.devicePixelRatio || 1;
//       ctx.save();
//       ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      
//       ctx.fillStyle = theme === "dark" ? "#000000" : "#ffffff";
//       ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr);

//       if (showGrid) {
//         ctx.strokeStyle = theme === "dark" ? "#555" : "#ccc";
//         ctx.lineWidth = 0.5;

//         for (let x = 0; x < canvas.width / dpr; x += gridSize) {
//           ctx.beginPath();
//           ctx.moveTo(x, 0);
//           ctx.lineTo(x, canvas.height / dpr);
//           ctx.stroke();
//         }
//         for (let y = 0; y < canvas.height / dpr; y += gridSize) {
//           ctx.beginPath();
//           ctx.moveTo(0, y);
//           ctx.lineTo(canvas.width / dpr, y);
//           ctx.stroke();
//         }
//       }

//       dots.forEach((dot) => {
//         ctx.fillStyle = theme === "dark" ? "yellow" : "red";
//         ctx.beginPath();
//         ctx.arc(dot.x, dot.y, 4, 0, 2 * Math.PI);
//         ctx.fill();
//       });
      
//       ctx.restore();
//     }

//     function handleClick(event) {
//       const rect = canvas.getBoundingClientRect();
//       const x = event.clientX - rect.left;
//       const y = event.clientY - rect.top;

//       const snappedX = Math.round(x / gridSize) * gridSize;
//       const snappedY = Math.round(y / gridSize) * gridSize;

//       onAddDot({ x: snappedX, y: snappedY });
//     }

//     const ro = new ResizeObserver(resizeCanvas);
//     ro.observe(canvas.parentElement);
//     window.addEventListener("resize", resizeCanvas);
//     canvas.addEventListener("click", handleClick);

//     resizeCanvas();

//     return () => {
//       ro.disconnect();
//       window.removeEventListener("resize", resizeCanvas);
//       canvas.removeEventListener("click", handleClick);
//     };
//   }, [showGrid, theme, smallGrid, gridSize, dots, onAddDot, transform]);

//   return <canvas ref={canvasRef} style={{ display: "block" }} />;
// }

// export default CircuitCanvas;

import React from "react";

function CircuitCanvas({ showGrid, theme, smallGrid, dots, onAddDot }) {
  const canvasRef = React.useRef(null);
  const gridSize = smallGrid ? 10 : 20;
  
  const [transform, setTransform] = React.useState([0, 0, 1]);
  const [circuitArea, setCircuitArea] = React.useState({ x: 0, y: 0, width: 0, height: 0 });
  const [mouseMode, setMouseMode] = React.useState("SELECT");
  const [mouseDragging, setMouseDragging] = React.useState(false);
  const [dragElm, setDragElm] = React.useState(null);
  const [initDragX, setInitDragX] = React.useState(0);
  const [initDragY, setInitDragY] = React.useState(0);

  // Transform functions
  const transformX = (x) => (x - transform[0]) * transform[2];
  const transformY = (y) => (y - transform[1]) * transform[2];
  const inverseTransformX = (x) => x / transform[2] + transform[0];
  const inverseTransformY = (y) => y / transform[2] + transform[1];

  React.useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    
    // Set context properties
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    function resizeCanvas() {
      const rect = canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      
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

      dots.forEach((dot) => {
        ctx.fillStyle = theme === "dark" ? "yellow" : "red";
        ctx.beginPath();
        ctx.arc(dot.x, dot.y, 4, 0, 2 * Math.PI);
        ctx.fill();
      });
      
      ctx.restore();
    }

    function handleClick(event) {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const snappedX = Math.round(x / gridSize) * gridSize;
      const snappedY = Math.round(y / gridSize) * gridSize;

      onAddDot({ x: snappedX, y: snappedY });
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
  }, [showGrid, theme, smallGrid, gridSize, dots, onAddDot, transform]);

  return <canvas ref={canvasRef} style={{ display: "block" }} />;
}

export default CircuitCanvas;