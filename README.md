# ElektraSage

## Introduction

ElektraSage is a one-stop shop for all your electronic needs especially in design & simulation.

### Current Features:
1. Normal Analog and Digital Simulations
2. Very Basic Microcontroller I/O Support
3. Very Basic Functional AI Support using RAG

### Features Planned
1. SPICE Integration
2. Verilog/HDL Integration (Simulation Only)
3. Better Sensor and Microcontroller Integration (Behavioral Simulation Only)

This project is based on CircuitJS1 originally a Java Applet Created by Paul Falstad and then later it was adapted by Iain Sharp to run in the browser using GWT.

For a hosted version of the application see:

* Paul's Page: [http://www.falstad.com/circuit/](http://www.falstad.com/circuit/)
* Iain's Page: [http://lushprojects.com/circuitjs/](http://lushprojects.com/circuitjs/)

Thanks to: Edward Calver for 15 new components and other improvements; Rodrigo Hausen for file import/export and many other UI improvements; J. Mike Rollins for the Zener diode code; Julius Schmidt for the spark gap code and some examples; Dustin Soodak for help with the user interface improvements; Jacob Calvert for the T Flip Flop; Ben Hayden for scope spectrum; Thomas Reitinger, Krystian Sławiński, Usevalad Khatkevich, Lucio Sciamanna, Mauro Hemerly Gazzani, J. Miguel Silva, and Franck Viard for translations; Andre Adrian for improved emitter coupled oscillator; Felthry for many examples; Colin Howell for code improvements. LZString (c) 2013 pieroxy.

## Tool Usage
The UI is simple drag and drop with support to famous shortcuts from simulators like LTSpice, for more info refer the documentation given by [Paul Falstad's CircuitJS1](https://github.com/pfalstad/circuitjs1), for AI Usage setup the LLM and other models as instructed below. Once setup you can simply enter your queries by clicking on the <code> AI Assistant </code> option and then entering your query like this:

<img width="2879" height="1532" alt="image" src="https://github.com/user-attachments/assets/c01b8a07-f3c0-4f2b-a681-4a8001292c18" />

You can then import the circuit once it is generated

> NOTE:  the Accuracy of AI generated circuits is not guaranteed and it pretty low for now it depends greatly on the LLM you use and other factors.

Microcontroller Support:
It is very basic and breaks a lot for the time being only <code>Arduino Uno</code> is supported, you can only do <code>digitalWrite</code> commands properly.

<img width="2879" height="1532" alt="image" src="https://github.com/user-attachments/assets/ca91bd4b-c216-44fc-9376-dd01fd400c33" />

You can either use some example codes or write your own Custom Sketches like you would on Arduino IDE


## LLM Selection and Integration
For our usage we have used <code> LLama 3.3 70B - Versatile </code> through <code> [GROQ](https://console.groq.com/home) </code>, for this you will have to sign up and create a account.

But you can certainly use your LLMs either local or cloud, for local LLMs you will have to create separate arrangements. 

After you get your API for LLM, you will have to change API settings in the file:

1. <code> add/rag_inference_groq.py </code>
2. <code> add/rag_api_server.py </code>
3. Add API key to <code>.env</code> and make sure this file remains listed in <code>.gitignore</code>

We are working on making this plug and play but for the time being this is what has to be done.

## Chunking and Embedding (RAG)
We have already added embeddings in file <code>embeddings.joblib</code> for now but if you want to chunk and embed yourself, you will have two options
1. Do it our way: Using <code>BGE-M3</code> model from Ollama, we already have used it and the code works with it by default, you will have to setup Ollama on your host and download the models

2. Or you can setup it yourself using tools you like, for this you will have to make changes to the file: <code> add/chunks_embed.py </code>. 

## Building the web application

The web application can be compiled and run locally in a local docker container.
We recommend running it on containers as this tool uses specific versions of Gradle only accessible through their github repo. 

## Docker/podman containers

### Building and Running Circuitjs in docker containers

*(replace the podman command with docker if you prefer docker)*

- To build Docker image using podman: 

```
podman build -f circuitjs1.Containerfile -t circuitjs1:latest
```

- To then run Docker image using podman:

```
podman run --name=circuitjs1 --rm -d -p 8000:8000 circuitjs1:latest
```

CircuitJS1 should be accessible at: http://localhost:8000/circuitjs.html


### Development using docker containers

(replace the podman command with docker if you prefer docker)

- To build the development Docker image using podman: 

```
podman build -f dev-start.Containerfile -t circuitjs1-dev:latest
```

CircuitJS1 should be accessible at: http://localhost:8000/circuitjs.html

If you need to modify the files while the container is running (using the gwt auto-build method):

```
podman run --rm -it --env-file .env -v $(pwd):/src:Z  --network host circuitjs1-dev:latest
```

This will use the current directory inside the container.


## Embedding

You can link to the full page version of the application using the link shown above.

If you want to embed the application in another page then use an iframe with the src being the full-page version.

You can add query parameters to link to change the applications startup behaviour. The following are supported:
```
.../circuitjs.html?cct=<string> // Load the circuit from the URL (like the # in the Java version)
.../circuitjs.html?ctz=<string> // Load the circuit from compressed data in the URL
.../circuitjs.html?startCircuit=<filename> // Loads the circuit named "filename" from the "Circuits" directory
.../circuitjs.html?startCircuitLink=<URL> // Loads the circuit from the specified URL. CURRENTLY THE URL MUST BE A DROPBOX SHARED FILE OR ANOTHER URL THAT SUPPORTS CORS ACCESS FROM THE CLIENT
.../circuitjs.html?euroResistors=true // Set to true to force "Euro" style resistors. If not specified the resistor style will be based on the user's browser's language preferences
.../circuitjs.html?IECGates=true // Set to true to force IEC logic gates. If not specified the gate style will be based on the user's browser's language preferences
.../circuitjs.html?usResistors=true // Set to true to force "US" style resistors. If not specified the resistor style will be based on the user's browser's language preferences
.../circuitjs.html?whiteBackground=<true|false>
.../circuitjs.html?conventionalCurrent=<true|false>
.../circuitjs.html?running=<true|false> // Start the app without the simulation running, default true
.../circuitjs.html?hideSidebar=<true|false> // Hide the sidebar, default false
.../circuitjs.html?hideMenu=<true|false> // Hide the menu, default false
.../circuitjs.html?editable=<true|false> // Allow circuit editing, default true
.../circuitjs.html?positiveColor=%2300ff00 // change positive voltage color (rrggbb)
.../circuitjs.html?negativeColor=%23ff0000 // change negative voltage color
.../circuitjs.html?selectColor=%2300ffff // change selection color
.../circuitjs.html?currentColor=%23ffff00 // change current color
.../circuitjs.html?mouseWheelEdit=<true|false> // allow changing of values by mouse wheel
.../circuitjs.html?mouseMode=<item> // set the initial mouse mode.  can also initially perform other UI actions, such as opening the 'about' menu, running 'importfromlocalfile', etc.
.../circuitjs.html?hideInfoBox=<true|false>
```
The simulator can also interface with your javascript code.  See [war/jsinterface.html](http://www.falstad.com/circuit/jsinterface.html) for an example.

## Building an Electron application

The [Electron](https://electronjs.org/) project allows web applications to be distributed as local executables for a variety of platforms. This repository contains the additional files needed to build circuitJS1 as an Electron application.

The general approach to building an Electron application for a particular platform is documented [here](https://electronjs.org/docs/tutorial/application-distribution). The following instructions apply this approach to circuit JS.

To build the Electron application:
* Compile the application using GWT, as above.
* Download and unpack a [pre-built Electron binary directory](https://github.com/electron/electron/releases) version 9.3.2 for the target platform.
* Copy the "app" directory from this repository to the location specified [here](https://electronjs.org/docs/tutorial/application-distribution) in the Electron binary directory structure.
* Copy the "war" directory, containing the compiled CircuitJS1 application, in to the "app" directory the Electron binary directory structure.
* Run the "Electron" executable file. It should automatically load CircuitJS1.

Known limitations of the Electron application:
* "Create short URL" on "Export as URL" doesn't work as it relies on server support.

Thanks to @Immortalin for the initial work in applying Electron to CircuitJS1.

## License

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
