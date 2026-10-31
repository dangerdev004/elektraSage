/*    
    Copyright (C) Paul Falstad and Iain Sharp
    
    This file is part of CircuitJS1.

    CircuitJS1 is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    CircuitJS1 is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CircuitJS1.  If not, see <http://www.gnu.org/licenses/>.
*/

package com.lushprojects.circuitjs1.client;

import com.google.gwt.user.client.ui.TextArea;
import com.google.gwt.user.client.ui.TextBox;
import com.google.gwt.user.client.ui.Button;
import com.google.gwt.user.client.ui.VerticalPanel;
import com.google.gwt.user.client.ui.HorizontalPanel;
import com.google.gwt.user.client.ui.ScrollPanel;
import com.google.gwt.user.client.ui.HTML;
import com.lushprojects.circuitjs1.client.util.Locale;
import com.google.gwt.event.dom.client.ClickHandler;
import com.google.gwt.event.dom.client.ClickEvent;
import com.google.gwt.event.dom.client.KeyCodes;
import com.google.gwt.event.dom.client.KeyPressEvent;
import com.google.gwt.event.dom.client.KeyPressHandler;
import com.google.gwt.user.client.ui.Label;
import com.google.gwt.user.client.ui.HasHorizontalAlignment;
import com.google.gwt.http.client.Request;
import com.google.gwt.http.client.RequestBuilder;
import com.google.gwt.http.client.RequestCallback;
import com.google.gwt.http.client.RequestException;
import com.google.gwt.http.client.Response;
import com.google.gwt.json.client.JSONObject;
import com.google.gwt.json.client.JSONParser;
import com.google.gwt.json.client.JSONString;
import com.google.gwt.json.client.JSONValue;

public class AIChatbotDialog extends Dialog {
	
    VerticalPanel mainPanel;
    VerticalPanel chatPanel;
    ScrollPanel scrollPanel;
    HorizontalPanel inputPanel;
    TextBox inputBox;
    Button sendButton;
    Button clearButton;
    Button importButton;
    CirSim sim;
    String lastCircuitText = null;
    
    // Configure your RAG API server URL here
    private static final String RAG_API_URL = "http://localhost:5000";
    private boolean isWaitingForResponse = false;
	
    public AIChatbotDialog(CirSim asim) {
        super();
        sim = asim;
        closeOnEnter = false;
        
        mainPanel = new VerticalPanel();
        mainPanel.setWidth("500px");
        setWidget(mainPanel);
        setText(Locale.LS("AI Chatbot Assistant"));
        
        // Welcome message
        Label welcomeLabel = new Label(Locale.LS("Ask me anything about circuits!"));
        welcomeLabel.setStyleName("topSpace");
        mainPanel.add(welcomeLabel);
        
        // Chat display area
        chatPanel = new VerticalPanel();
        chatPanel.setWidth("100%");
        chatPanel.setStyleName("chatPanel");
        
        scrollPanel = new ScrollPanel();
        scrollPanel.setWidth("480px");
        scrollPanel.setHeight("300px");
        scrollPanel.add(chatPanel);
        scrollPanel.getElement().getStyle().setProperty("border", "1px solid #ccc");
        scrollPanel.getElement().getStyle().setProperty("backgroundColor", "#f9f9f9");
        scrollPanel.getElement().getStyle().setProperty("padding", "10px");
        mainPanel.add(scrollPanel);
        
        // Add initial welcome message to chat
        addMessageToChat("AI Assistant", "Hello! I'm your circuit assistant. Ask me about components, circuit design, or troubleshooting!", true);
        
        // Input area
        inputPanel = new HorizontalPanel();
        inputPanel.setWidth("100%");
        inputPanel.setSpacing(5);
        inputPanel.setStyleName("topSpace");
        
        inputBox = new TextBox();
        inputBox.setWidth("350px");
        inputBox.getElement().setAttribute("placeholder", "Type your question here...");
        
        // Handle Enter key press
        inputBox.addKeyPressHandler(new KeyPressHandler() {
            public void onKeyPress(KeyPressEvent event) {
                if (event.getCharCode() == KeyCodes.KEY_ENTER) {
                    sendMessage();
                }
            }
        });
        
        sendButton = new Button(Locale.LS("Send"));
        sendButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                sendMessage();
            }
        });
        
        clearButton = new Button(Locale.LS("Clear"));
        clearButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                clearChat();
            }
        });
        
        importButton = new Button(Locale.LS("Import Circuit"));
        importButton.setEnabled(false);
        importButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                importCircuit();
            }
        });
        
        inputPanel.add(inputBox);
        inputPanel.add(sendButton);
        inputPanel.add(clearButton);
        inputPanel.add(importButton);
        mainPanel.add(inputPanel);
        
        // Close button
        HorizontalPanel buttonPanel = new HorizontalPanel();
        buttonPanel.setWidth("100%");
        buttonPanel.setHorizontalAlignment(HasHorizontalAlignment.ALIGN_RIGHT);
        buttonPanel.setStyleName("topSpace");
        
        Button closeButton = new Button(Locale.LS("Close"));
        closeButton.addClickHandler(new ClickHandler() {
            public void onClick(ClickEvent event) {
                closeDialog();
            }
        });
        buttonPanel.add(closeButton);
        mainPanel.add(buttonPanel);
        
        this.center();
        show();
    }
    
    private void sendMessage() {
        String message = inputBox.getText().trim();
        if (message.isEmpty()) {
            return;
        }
        
        if (isWaitingForResponse) {
            addMessageToChat("System", "Please wait for the current response to complete.", true);
            return;
        }
        
        // Add user message to chat
        addMessageToChat("You", message, false);
        
        // Clear input and disable send button
        inputBox.setText("");
        sendButton.setEnabled(false);
        isWaitingForResponse = true;
        
        // Show loading indicator
        addMessageToChat("AI Assistant", "Thinking... (analyzing circuits and generating response)", true);
        
        // Process message and get response from RAG API
        processMessageWithRAG(message);
    }
    
    private void processMessageWithRAG(final String message) {
        // Determine if this is a circuit generation request or simple question
        String lowerMessage = message.toLowerCase();
        boolean isCircuitRequest = lowerMessage.contains("circuit") || 
                                   lowerMessage.contains("generate") ||
                                   lowerMessage.contains("create") ||
                                   lowerMessage.contains("design") ||
                                   lowerMessage.contains("build");
        
        String endpoint = isCircuitRequest ? "/query" : "/simple-query";
        String url = RAG_API_URL + endpoint;
        
        // Build JSON request
        JSONObject requestData = new JSONObject();
        requestData.put("query", new JSONString(message));
        
        RequestBuilder builder = new RequestBuilder(RequestBuilder.POST, url);
        builder.setHeader("Content-Type", "application/json");
        
        try {
            builder.sendRequest(requestData.toString(), new RequestCallback() {
                public void onResponseReceived(Request request, Response response) {
                    // Remove loading message
                    removeLastMessage();
                    
                    sendButton.setEnabled(true);
                    isWaitingForResponse = false;
                    
                    if (response.getStatusCode() == 200) {
                        try {
                            JSONValue jsonValue = JSONParser.parseStrict(response.getText());
                            JSONObject jsonObj = jsonValue.isObject();
                            
                            if (jsonObj != null) {
                                JSONValue successValue = jsonObj.get("success");
                                boolean success = successValue != null && successValue.isBoolean().booleanValue();
                                
                                if (success) {
                                    JSONValue responseValue = jsonObj.get("response");
                                    String responseText = responseValue != null ? responseValue.isString().stringValue() : "No response received";
                                    
                                    // Check if circuit text is available
                                    JSONValue circuitValue = jsonObj.get("circuit_text");
                                    if (circuitValue != null && circuitValue.isString() != null) {
                                        lastCircuitText = circuitValue.isString().stringValue();
                                        importButton.setEnabled(true);
                                        responseText += "<br/><br/><b>Circuit generated!</b> Click 'Import Circuit' to load it into the simulator.";
                                    }
                                    
                                    addMessageToChat("AI Assistant", responseText, true);
                                } else {
                                    JSONValue errorValue = jsonObj.get("error");
                                    String errorMsg = errorValue != null ? errorValue.isString().stringValue() : "Unknown error";
                                    addMessageToChat("AI Assistant", "Error: " + errorMsg, true);
                                }
                            }
                        } catch (Exception e) {
                            addMessageToChat("AI Assistant", "Error parsing response: " + e.getMessage(), true);
                        }
                    } else {
                        addMessageToChat("AI Assistant", "Server error (HTTP " + response.getStatusCode() + "). Make sure the RAG API server is running on port 5000.", true);
                    }
                }
                
                public void onError(Request request, Throwable exception) {
                    // Remove loading message
                    removeLastMessage();
                    
                    sendButton.setEnabled(true);
                    isWaitingForResponse = false;
                    
                    addMessageToChat("AI Assistant", 
                        "Connection error: " + exception.getMessage() + 
                        "<br/><br/>Please ensure the RAG API server is running:<br/>" +
                        "1. Navigate to the 'add' directory<br/>" +
                        "2. Run: python rag_api_server.py<br/>" +
                        "3. Server should be accessible at " + RAG_API_URL, true);
                }
            });
        } catch (RequestException e) {
            // Remove loading message
            removeLastMessage();
            
            sendButton.setEnabled(true);
            isWaitingForResponse = false;
            
            addMessageToChat("AI Assistant", "Failed to send request: " + e.getMessage(), true);
        }
    }
    
    private void importCircuit() {
        if (lastCircuitText != null && !lastCircuitText.isEmpty()) {
            sim.pushUndo();
            sim.importCircuitFromText(lastCircuitText, false);
            addMessageToChat("System", "Circuit imported successfully!", true);
            importButton.setEnabled(false);
            lastCircuitText = null;
        }
    }
    
    private void removeLastMessage() {
        int count = chatPanel.getWidgetCount();
        if (count > 0) {
            chatPanel.remove(count - 1);
        }
    }
    
    private void addMessageToChat(String sender, String message, boolean isAI) {
        HorizontalPanel messagePanel = new HorizontalPanel();
        messagePanel.setWidth("100%");
        messagePanel.setSpacing(5);
        
        // Create message container
        VerticalPanel msgContainer = new VerticalPanel();
        
        // Sender label
        Label senderLabel = new Label(sender + ":");
        senderLabel.getElement().getStyle().setProperty("fontWeight", "bold");
        senderLabel.getElement().getStyle().setProperty("color", isAI ? "#0066cc" : "#006600");
        msgContainer.add(senderLabel);
        
        // Message content
        HTML messageHTML = new HTML(message);
        messageHTML.getElement().getStyle().setProperty("marginLeft", "10px");
        messageHTML.getElement().getStyle().setProperty("padding", "5px");
        messageHTML.getElement().getStyle().setProperty("backgroundColor", isAI ? "#e3f2fd" : "#e8f5e9");
        messageHTML.getElement().getStyle().setProperty("borderRadius", "5px");
        messageHTML.getElement().getStyle().setProperty("marginBottom", "10px");
        msgContainer.add(messageHTML);
        
        messagePanel.add(msgContainer);
        chatPanel.add(messagePanel);
        
        // Scroll to bottom
        scrollPanel.scrollToBottom();
    }
    
    private void clearChat() {
        chatPanel.clear();
        lastCircuitText = null;
        importButton.setEnabled(false);
        addMessageToChat("AI Assistant", "Chat cleared. How can I help you?", true);
    }
}
