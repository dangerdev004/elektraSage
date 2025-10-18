// import React, { useState } from "react";
// import "./Toolbar.css";

// const menus = [
//   {
//     name: "File",
//     items: [],
//   },
//   {
//     name: "Edit",
//     items: [
//       "Undo",
//       "Redo",
//       "Cut",
//       "Copy",
//       "Duplicate",
//       "Select All",
//       "Find Component",
//       "Center Circuit",
//       "Zoom 100%",
//       "Zoom In",
//       "Zoom Out",
//       "Flip X",
//       "Flip Y",
//       "Flip XY",
//     ],
//   },
//   {
//     name: "Draw",
//     items: [
//       "Add Wire",
//       "Add Resistor",
//       "Passive Components",
//       "Inputs and Sources",
//       "Outputs and Labels",
//       "Active Components",
//       "Active Building Blocks",
//       "Logic Gates, Input and Output",
//       "Digital Chips",
//       "Analog and Hybrid Chips",
//       "Subcircuits",
//       "Drag",
//       "Select/Drag Sel",
//     ],
//   },
//   {
//     name: "Scopes",
//     items: ["Stack All", "Unstack All", "Combine All", "Separate All"],
//   },
//   {
//     name: "Options",
//     items: [
//       "Show Current",
//       "Show Voltage",
//       "Show Power",
//       "Show Values",
//       "Show Grid",
//       "Small Grid",
//       "Toolbar",
//       "Show Cursor Cross Hairs",
//       "European Resistors",
//       "IEC Gates",
//       "White Background",
//       "Conventional Current Motion",
//       "Disable Editing",
//       "Edit Values With Mouse Wheel",
//       "Shortcuts...",
//       "Subcircuits...",
//       "Other Options...",
//     ],
//   },
//   {
//     name: "Circuits",
//     items: [
//       "Basics",
//       "A/C Circuits",
//       "Passive Filters",
//       "Other Passive Circuits",
//       "Diodes",
//       "Op-Amps",
//       "Transistors",
//       "MOSFETs",
//       "555 Timer Chip",
//       "Active Filters",
//       "Logic Families",
//       "Combinational Logic",
//       "Sequential Logic",
//       "Analog/Digital",
//       "Power Converters",
//       "Phase-Locked Loops",
//       "Transmission Lines",
//       "Misc Devices",
//       "Blank Circuit",
//     ],
//   },
// ];

// export default function Toolbar({
//   showGrid,
//   onToggleGrid,
//   theme,
//   onToggleTheme,
//   smallGrid,
//   onToggleSmallGrid,
//   fileActions,
// }) {
//   const [openMenu, setOpenMenu] = useState(null);

//   const handleClick = (menuName, item) => {
//     console.log(`Clicked: ${menuName} → ${item}`);

//     // 🔹 Make "Show Grid" interactive
//     if (menuName === "Options" && item === "Show Grid") {
//       onToggleGrid(); // calls back to App.js
//       return;
//     }
//     if (menuName === "Options" && item === "White Background") {
//       onToggleTheme(); // 🔹 calls App.js function
//     }
//     if (menuName === "Options" && item === "Small Grid") {
//       onToggleSmallGrid(); // 🔹 calls App.js function
//     }

//     // Later: add more actions for other items here
//   };

//   return (
//     <div className="toolbar">
//       {menus.map((menu) => (
//         <div
//           key={menu.name}
//           className="menu-item"
//           onMouseEnter={() => setOpenMenu(menu.name)}
//           onMouseLeave={() => setOpenMenu(null)}
//         >
//           {menu.name}
//           {openMenu === menu.name && (
//             <div className={`dropdown dropdown-${menu.name.toLowerCase()}`}>
//               <ul>
//                 {menu.items.map((item) => (
//                   <li key={item} onClick={() => handleClick(menu.name, item)}>
//                     {menu.name === "Options" && item === "Show Grid" ? (
//                       <>
//                         {showGrid ? "✓ " : ""} {item}
//                       </>
//                     ) : menu.name === "Options" &&
//                       item === "White Background" ? (
//                       <>
//                         {theme === "light" ? "✓ " : ""} {item}
//                       </>
//                     ) : menu.name === "Options" && item === "Small Grid" ? (
//                       <>
//                         {smallGrid ? "✓ " : ""} {item}
//                       </>
//                     ) : (
//                       item
//                     )}
//                   </li>
//                 ))}
//               </ul>
//               {menu.name === "File" && (
//                 <ul>
//                   <li onClick={fileActions.newBlank}>New Blank Circuit</li>
//                   <li onClick={fileActions.openFile}>Open File</li>
//                   <li onClick={fileActions.importText}>Import From Text</li>
//                   <li onClick={fileActions.saveAs}>Save As</li>
//                   <li onClick={fileActions.exportLink}>Export as Link</li>
//                   <li onClick={fileActions.exportText}>Export as Text</li>
//                   <li onClick={fileActions.exportImage}>Export as Image</li>
//                   <li onClick={fileActions.copyImage}>
//                     Copy Circuit Image to Clipboard
//                   </li>
//                   <li onClick={fileActions.exportSvg}>Export as SVG</li>
//                   <li onClick={fileActions.createSubcircuit}>
//                     Create Subcircuit
//                   </li>
//                   <li onClick={fileActions.findDC}>Find DC Operating Point</li>
//                   <li onClick={fileActions.recover}>Recover Auto-Save</li>
//                   <li onClick={fileActions.print}>Print</li>
//                   <li onClick={fileActions.toggleFullscreen}>
//                     Toggle Full Screen
//                   </li>
//                   <li onClick={fileActions.about}>About..</li>
//                 </ul>
//               )}
//             </div>
//           )}
//         </div>
//       ))}
//     </div>
//   );
// }

import React, { useState } from "react";
import "./Toolbar.css";

const menus = [
  {
    name: "File",
    items: [],
  },
  {
    name: "Edit",
    items: [
      "Undo",
      "Redo",
      "Cut",
      "Copy",
      "Duplicate",
      "Select All",
      "Find Component",
      "Center Circuit",
      "Zoom 100%",
      "Zoom In",
      "Zoom Out",
      "Flip X",
      "Flip Y",
      "Flip XY",
    ],
  },
  {
    name: "Draw",
    items: [
      "Add Wire",
      "Add Resistor",
      "Passive Components",
      "Inputs and Sources",
      "Outputs and Labels",
      "Active Components",
      "Active Building Blocks",
      "Logic Gates, Input and Output",
      "Digital Chips",
      "Analog and Hybrid Chips",
      "Subcircuits",
      "Drag",
      "Select/Drag Sel",
    ],
  },
  {
    name: "Scopes",
    items: ["Stack All", "Unstack All", "Combine All", "Separate All"],
  },
  {
    name: "Options",
    items: [
      "Show Current",
      "Show Voltage",
      "Show Power",
      "Show Values",
      "Show Grid",
      "Small Grid",
      "Toolbar",
      "Show Cursor Cross Hairs",
      "European Resistors",
      "IEC Gates",
      "White Background",
      "Conventional Current Motion",
      "Disable Editing",
      "Edit Values With Mouse Wheel",
      "Shortcuts...",
      "Subcircuits...",
      "Other Options...",
    ],
  },
  {
    name: "Circuits",
    items: [
      "Basics",
      "A/C Circuits",
      "Passive Filters",
      "Other Passive Circuits",
      "Diodes",
      "Op-Amps",
      "Transistors",
      "MOSFETs",
      "555 Timer Chip",
      "Active Filters",
      "Logic Families",
      "Combinational Logic",
      "Sequential Logic",
      "Analog/Digital",
      "Power Converters",
      "Phase-Locked Loops",
      "Transmission Lines",
      "Misc Devices",
      "Blank Circuit",
    ],
  },
];

export default function Toolbar({
  showGrid,
  onToggleGrid,
  theme,
  onToggleTheme,
  smallGrid,
  onToggleSmallGrid,
  fileActions,
}) {
  const [openMenu, setOpenMenu] = useState(null);
  
  // New state variables for Options menu
  const [showCurrent, setShowCurrent] = useState(false);
  const [showVoltage, setShowVoltage] = useState(true);
  const [showPower, setShowPower] = useState(false);
  const [showValues, setShowValues] = useState(true);
  const [showToolbar, setShowToolbar] = useState(true);
  const [showCrosshairs, setShowCrosshairs] = useState(false);
  const [euroResistors, setEuroResistors] = useState(false);
  const [iecGates, setIecGates] = useState(false);
  const [conventionalCurrent, setConventionalCurrent] = useState(true);
  const [disableEditing, setDisableEditing] = useState(false);
  const [mouseWheelEdit, setMouseWheelEdit] = useState(true);

  const getCheckmark = (menuName, item) => {
    if (menuName !== "Options") return "";
    
    const checks = {
      "Show Grid": showGrid,
      "White Background": theme === "light",
      "Small Grid": smallGrid,
      "Show Current": showCurrent,
      "Show Voltage": showVoltage,
      "Show Power": showPower,
      "Show Values": showValues,
      "Toolbar": showToolbar,
      "Show Cursor Cross Hairs": showCrosshairs,
      "European Resistors": euroResistors,
      "IEC Gates": iecGates,
      "Conventional Current Motion": conventionalCurrent,
      "Disable Editing": disableEditing,
      "Edit Values With Mouse Wheel": mouseWheelEdit,
    };
    
    return checks[item] ? "✓ " : "";
  };

  const handleClick = (menuName, item) => {
    console.log(`Clicked: ${menuName} → ${item}`);

    if (menuName === "Options") {
      switch (item) {
        case "Show Grid":
          onToggleGrid();
          break;
        case "White Background":
          onToggleTheme();
          break;
        case "Small Grid":
          onToggleSmallGrid();
          break;
        case "Show Current":
          setShowCurrent(!showCurrent);
          break;
        case "Show Voltage":
          setShowVoltage(!showVoltage);
          if (!showVoltage) setShowPower(false);
          break;
        case "Show Power":
          setShowPower(!showPower);
          if (!showPower) setShowVoltage(false);
          break;
        case "Show Values":
          setShowValues(!showValues);
          break;
        case "Toolbar":
          setShowToolbar(!showToolbar);
          break;
        case "Show Cursor Cross Hairs":
          setShowCrosshairs(!showCrosshairs);
          break;
        case "European Resistors":
          setEuroResistors(!euroResistors);
          break;
        case "IEC Gates":
          setIecGates(!iecGates);
          break;
        case "Conventional Current Motion":
          setConventionalCurrent(!conventionalCurrent);
          break;
        case "Disable Editing":
          setDisableEditing(!disableEditing);
          break;
        case "Edit Values With Mouse Wheel":
          setMouseWheelEdit(!mouseWheelEdit);
          break;
        case "Shortcuts...":
          console.log("Open Shortcuts Dialog");
          break;
        case "Subcircuits...":
          console.log("Open Subcircuits Dialog");
          break;
        case "Other Options...":
          console.log("Open Other Options Dialog");
          break;
      }
    }

    if (menuName === "Edit") {
      switch (item) {
        case "Undo":
        case "Redo":
        case "Cut":
        case "Copy":
        case "Duplicate":
        case "Select All":
          console.log(`${item} action`);
          break;
      }
    }

    if (menuName === "Scopes") {
      console.log(`${item} scopes`);
    }
  };

  return (
    <div className="toolbar">
      {menus.map((menu) => (
        <div
          key={menu.name}
          className="menu-item"
          onMouseEnter={() => setOpenMenu(menu.name)}
          onMouseLeave={() => setOpenMenu(null)}
        >
          {menu.name}
          {openMenu === menu.name && (
            <div className={`dropdown dropdown-${menu.name.toLowerCase()}`}>
              <ul>
                {menu.items.map((item) => (
                  <li key={item} onClick={() => handleClick(menu.name, item)}>
                    {getCheckmark(menu.name, item)} {item}
                  </li>
                ))}
              </ul>
              {menu.name === "File" && (
                <ul>
                  <li onClick={fileActions.newBlank}>New Blank Circuit</li>
                  <li onClick={fileActions.openFile}>Open File</li>
                  <li onClick={fileActions.importText}>Import From Text</li>
                  <li onClick={fileActions.saveAs}>Save As</li>
                  <li onClick={fileActions.exportLink}>Export as Link</li>
                  <li onClick={fileActions.exportText}>Export as Text</li>
                  <li onClick={fileActions.exportImage}>Export as Image</li>
                  <li onClick={fileActions.copyImage}>
                    Copy Circuit Image to Clipboard
                  </li>
                  <li onClick={fileActions.exportSvg}>Export as SVG</li>
                  <li onClick={fileActions.createSubcircuit}>
                    Create Subcircuit
                  </li>
                  <li onClick={fileActions.findDC}>Find DC Operating Point</li>
                  <li onClick={fileActions.recover}>Recover Auto-Save</li>
                  <li onClick={fileActions.print}>Print</li>
                  <li onClick={fileActions.toggleFullscreen}>
                    Toggle Full Screen
                  </li>
                  <li onClick={fileActions.about}>About..</li>
                </ul>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}