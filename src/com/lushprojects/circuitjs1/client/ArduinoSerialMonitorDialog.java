package com.lushprojects.circuitjs1.client;

import com.google.gwt.user.client.ui.Button;
import com.google.gwt.user.client.ui.TextArea;
import com.google.gwt.user.client.ui.VerticalPanel;
import com.google.gwt.user.client.ui.Label;
import com.google.gwt.user.client.ui.HorizontalPanel;
import com.google.gwt.event.dom.client.ClickHandler;
import com.google.gwt.event.dom.client.ClickEvent;
import com.google.gwt.user.client.Timer;

/**
 * Dialog for viewing Arduino Serial Monitor output
 */
public class ArduinoSerialMonitorDialog extends Dialog {
    
    private ArduinoElm arduinoElm;
    private TextArea outputArea;
    private Button clearButton;
    private Button closeButton;
    private Button refreshButton;
    private Timer updateTimer;
    
    public ArduinoSerialMonitorDialog(ArduinoElm elm) {
        super();
        this.arduinoElm = elm;
        
        VerticalPanel vp = new VerticalPanel();
        vp.setWidth("600px");
        
        // Title
        Label titleLabel = new Label("Arduino Serial Monitor");
        titleLabel.addStyleName("topSpace");
        vp.add(titleLabel);
        
        // Status
        String mode = arduinoElm.isRunning() ? "Running" : "Stopped";
        Label statusLabel = new Label("Status: " + mode);
        statusLabel.addStyleName("topSpace");
        vp.add(statusLabel);
        
        // Output text area
        outputArea = new TextArea();
        outputArea.setWidth("580px");
        outputArea.setHeight("400px");
        outputArea.setReadOnly(true);
        outputArea.addStyleName("topSpace");
        vp.add(outputArea);
        
        // Update with current output
        updateOutput();
        
        // Buttons panel
        HorizontalPanel buttonPanel = new HorizontalPanel();
        buttonPanel.addStyleName("topSpace");
        
        refreshButton = new Button("Refresh");
        refreshButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                updateOutput();
            }
        });
        buttonPanel.add(refreshButton);
        
        clearButton = new Button("Clear");
        clearButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                clearOutput();
            }
        });
        buttonPanel.add(clearButton);
        
        closeButton = new Button("Close");
        closeButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                closeDialog();
            }
        });
        buttonPanel.add(closeButton);
        
        vp.add(buttonPanel);
        
        setWidget(vp);
        setText("Serial Monitor");
        center();
        
        // Auto-update every 500ms
        updateTimer = new Timer() {
            public void run() {
                updateOutput();
            }
        };
        updateTimer.scheduleRepeating(500);
    }
    
    private void updateOutput() {
        String output = arduinoElm.getSerialOutput();
        if (output != null && !output.isEmpty()) {
            outputArea.setText(output);
            // Auto-scroll to bottom
            outputArea.setCursorPos(output.length());
        }
    }
    
    private void clearOutput() {
        arduinoElm.clearSerialOutput();
        outputArea.setText("");
    }
    
    public void closeDialog() {
        if (updateTimer != null) {
            updateTimer.cancel();
        }
        hide();
    }
}