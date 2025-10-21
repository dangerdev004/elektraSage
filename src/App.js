import React, { useRef, useEffect ,useState } from "react";
import "./App.css";
import Toolbar from "./components/Toolbar";
import CircuitCanvas from "./components/CircuitCanvas";
import Sidebar from "./components/Sidebar";

function App() {
  const [showGrid, setShowGrid] = useState(false);
  const [theme, setTheme] = useState("dark");
  const [smallGrid, setSmallGrid] = useState(false);
  const [dots, setDots] = useState([]);

  const [simulationTime, setSimulationTime] = useState(0);
  const [simRunning, setSimRunning] = useState(false);
  const [speedValue, setSpeedValue] = useState(117);
  const [currentValue, setCurrentValue] = useState(50);
  const [powerValue, setPowerValue] = useState(50);
  const [circuitTitle, setCircuitTitle] = useState("Untitled Circuit");
  const animationFrameId = useRef(null);

  useEffect(() => {
    const runSimulation = () => {
      const timeStep = 5e-6;
      setSimulationTime((prevTime) => prevTime + timeStep);
        animationFrameId.current = requestAnimationFrame(runSimulation);
      };
      if (simRunning) {
        animationFrameId.current = requestAnimationFrame(runSimulation);
      } else {
          cancelAnimationFrame(animationFrameId.current);
      }
      return () => { 
        cancelAnimationFrame(animationFrameId.current);
      };
  }, [simRunning]);

  const handleReset = () => {
    setSimulationTime(0);
    // Additional reset logic can be added here
    console.log("Circuit simulation reset to t = 0");
  }
 
  const fileInputRef = React.useRef(null);

  // open file handler
  const openFile = () => {
    fileInputRef.current.click();
  };

  const handleFileSelected = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const circuit = JSON.parse(event.target.result);
        setDots(circuit.dots || []);
        alert("Circuit loaded!");
      } catch (err) {
        alert("Invalid file format");
      }
    };
    reader.readAsText(file);
  };

  const saveAs = () => {
    const dataStr = JSON.stringify({ dots });
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "circuit.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const importText = () => {
    const input = prompt("Paste circuit JSON here:");
    if (!input) return;
    try {
      const circuit = JSON.parse(input);
      setDots(circuit.dots || []);
      alert("Circuit imported!");
    } catch {
      alert("Invalid text format");
    }
  };

  const exportText = () => {
    const dataStr = JSON.stringify({ dots }, null, 2);
    navigator.clipboard.writeText(dataStr);
    alert("Circuit copied to clipboard as text!");
  };

  const exportImage = () => {
    const canvas = document.querySelector("canvas");
    const url = canvas.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = url;
    a.download = "circuit.png";
    a.click();
  };

  const copyImage = async () => {
    const canvas = document.querySelector("canvas");
    canvas.toBlob(async (blob) => {
      try {
        await navigator.clipboard.write([
          new ClipboardItem({ "image/png": blob }),
        ]);
        alert("Image copied to clipboard!");
      } catch (err) {
        alert("Clipboard image copy not supported in this browser");
      }
    });
  };

  const fileActions = {
    newBlank: () => setDots([]),
    openFile,
    importText,
    saveAs,
    exportLink: () => alert("Export as Link not implemented yet"),
    exportText,
    exportImage,
    copyImage,
    exportSvg: () => alert("Export as SVG not implemented yet"),
    createSubcircuit: () => alert("Not implemented yet"),
    findDC: () => alert("Not implemented yet"),
    recover: () => alert("Not implemented yet"),
    print: () => window.print(),
    toggleFullscreen: () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    },
    about: () => alert("CircuitJS1 Clone — React version"),
  };

  return (
    <div className="App">
      <input
        type="file"
        accept=".json"
        style={{ display: "none" }}
        ref={fileInputRef}
        onChange={handleFileSelected}
      />
      <Toolbar
        showGrid={showGrid}
        onToggleGrid={() => setShowGrid(!showGrid)}
        smallGrid={smallGrid}
        onToggleSmallGrid={() => setSmallGrid(!smallGrid)}
        theme={theme}
        onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        fileActions={fileActions}
      />
      <div className="workspace">
        <div className="canvas-wrapper">
          <CircuitCanvas
            showGrid={showGrid}
            theme={theme}
            smallGrid={smallGrid}
            dots={dots}
            onAddDot={(dot) => setDots([...dots, dot])}
          />
      </div>
      <Sidebar
        simRunning={simRunning}
        onToggleSimulation={() => setSimRunning(!simRunning)}
        onReset={handleReset}
        speedValue={speedValue}
        onSpeedChange={setSpeedValue}
        currentValue={currentValue}
        onCurrentChange={setCurrentValue}
        powerValue={powerValue}
        onPowerChange={setPowerValue}
        circuitTitle={circuitTitle}
        powerBarEnabled={true /* We can control this later */}
      />
    </div>
  </div>
  );
}
export default App;
