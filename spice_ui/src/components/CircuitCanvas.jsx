import { useEffect, useRef } from 'react';

// Thin React wrapper: the Editor owns the canvas, events and drawing.
export function CircuitCanvas({ editor }) {
  const wrapRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    editor.attach(canvasRef.current, wrapRef.current);
    return () => editor.detach();
  }, [editor]);

  return (
    <div className="canvas-wrap" ref={wrapRef}>
      <canvas ref={canvasRef} tabIndex={0} aria-label="Circuit canvas" />
    </div>
  );
}
