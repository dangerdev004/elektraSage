package com.lushprojects.circuitjs1.client;

import com.google.gwt.user.client.ui.Button;
import com.google.gwt.user.client.ui.TextArea;
import com.google.gwt.user.client.ui.VerticalPanel;
import com.google.gwt.user.client.ui.Label;
import com.google.gwt.event.dom.client.ClickHandler;
import com.google.gwt.event.dom.client.ClickEvent;

/**
 * Dialog for loading Arduino hex files into ArduinoElm
 */
public class LoadArduinoHexDialog extends Dialog {
    
    private ArduinoElm arduinoElm;
    private TextArea hexTextArea;
    private Button loadButton;
    private Button cancelButton;
    private Button clearButton;
    private Label statusLabel;
    
    public LoadArduinoHexDialog(ArduinoElm elm) {
        super();
        this.arduinoElm = elm;
        
        VerticalPanel vp = new VerticalPanel();
        vp.setWidth("500px");
        
        // Title
        Label titleLabel = new Label("Load Arduino Hex File");
        titleLabel.addStyleName("topSpace");
        vp.add(titleLabel);
        
        // Instructions
        Label instructLabel = new Label(
            "Paste your Arduino .hex file contents below.\n" +
            "To get a .hex file:\n" +
            "1. Compile your sketch in Arduino IDE\n" +
            "2. Go to Sketch → Export compiled Binary\n" +
            "3. Open the .hex file in a text editor and paste here"
        );
        instructLabel.addStyleName("topSpace");
        vp.add(instructLabel);
        
        // Text area for hex content
        hexTextArea = new TextArea();
        hexTextArea.setWidth("480px");
        hexTextArea.setHeight("300px");
        hexTextArea.addStyleName("topSpace");
        vp.add(hexTextArea);
        
        // Status label
        statusLabel = new Label("");
        statusLabel.addStyleName("topSpace");
        vp.add(statusLabel);
        
        // Check if already loaded
        if (arduinoElm.isRunning()) {
            statusLabel.setText("Status: Arduino is currently running");
        }
        
        // Buttons panel
        VerticalPanel buttonPanel = new VerticalPanel();
        buttonPanel.addStyleName("topSpace");
        
        loadButton = new Button("Load Hex File");
        loadButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                loadHexFile();
            }
        });
        buttonPanel.add(loadButton);
        
        clearButton = new Button("Stop AVR");
        clearButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                stopAVR();
            }
        });
        buttonPanel.add(clearButton);
        
        cancelButton = new Button("Cancel");
        cancelButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                closeDialog();
            }
        });
        buttonPanel.add(cancelButton);
        
        vp.add(buttonPanel);
        
        setWidget(vp);
        setText("Arduino Hex File Loader");
        center();
    }
    
    private void loadHexFile() {
        String hexContent = hexTextArea.getText().trim();
        
        if (hexContent.isEmpty()) {
            statusLabel.setText("Error: Please paste hex file content");
            return;
        }
        
        if (!hexContent.startsWith(":")) {
            statusLabel.setText("Error: Invalid hex file format (should start with ':')");
            return;
        }
        
        try {
            statusLabel.setText("Loading hex file...");
            arduinoElm.loadHexFile(hexContent);
            statusLabel.setText("Success! AVR8JS is now running your Arduino code.");
        } catch (Exception e) {
            statusLabel.setText("Error loading hex file: " + e.getMessage());
        }
    }
    
    private void stopAVR() {
        arduinoElm.stopAVR();
        statusLabel.setText("AVR stopped. Running in built-in mode.");
    }
    
    public void closeDialog() {
        hide();
    }
}