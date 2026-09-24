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
import com.google.gwt.http.client.URL;
import com.google.gwt.json.client.JSONArray;
import com.google.gwt.json.client.JSONObject;
import com.google.gwt.json.client.JSONParser;
import com.google.gwt.json.client.JSONString;
import com.google.gwt.json.client.JSONValue;
import com.google.gwt.safehtml.shared.SafeHtmlUtils;

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
    
    // Circuit agent (FastAPI) server: run `python app.py` inside the 'add' directory
    private static final String RAG_API_URL = "http://localhost:5000";
    private static final int REQUEST_TIMEOUT_MS = 120000;
    private boolean isWaitingForResponse = false;
    
    // Conversation id issued by the server; lets the agent remember earlier turns
    // (e.g. it asks for a missing cutoff frequency, then you answer it).
    // Also kept in sessionStorage, so closing and reopening the dialog (or
    // reloading the page) resumes the same conversation. The server keeps the
    // transcript (add/output/sessions/<id>.json) and serves it via /history.
    private String sessionId = null;
    private static final String SESSION_KEY = "elektrasage_chat_session";
    private static final String CIRCUIT_HINT = "<br/><br/><b>Circuit generated!</b> Click 'Import Circuit' to load it into the simulator.";
    
    private static native String storageGet(String key) /*-{
        try { return $wnd.sessionStorage.getItem(key); } catch (e) { return null; }
    }-*/;
    
    private static native void storageSet(String key, String value) /*-{
        try {
            if (value == null) { $wnd.sessionStorage.removeItem(key); }
            else { $wnd.sessionStorage.setItem(key, value); }
        } catch (e) {}
    }-*/;
    
    private void setSessionId(String id) {
        sessionId = id;
        storageSet(SESSION_KEY, id);
    }
	
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
        
        // Resume this browser session's conversation, if there is one
        sessionId = storageGet(SESSION_KEY);
        if (sessionId != null) {
            loadHistory();
        }
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
        
        // Add user message to chat (escaped: it is rendered as HTML)
        addMessageToChat("You", escapeHtml(message), false);
        
        // Clear input and disable send button
        inputBox.setText("");
        sendButton.setEnabled(false);
        isWaitingForResponse = true;
        
        // Show loading indicator
        addMessageToChat("AI Assistant", "Thinking... (analyzing circuits and generating response)", true);
        
        // Send to the circuit agent
        processMessageWithRAG(message);
    }
    
    // The agent decides for itself whether to ask a follow-up question or
    // generate a circuit, so every message goes to the same endpoint.
    private void processMessageWithRAG(final String message) {
        String url = RAG_API_URL + "/query";
        
        // Build JSON request
        JSONObject requestData = new JSONObject();
        requestData.put("query", new JSONString(message));
        if (sessionId != null) {
            requestData.put("session_id", new JSONString(sessionId));
        }
        
        RequestBuilder builder = new RequestBuilder(RequestBuilder.POST, url);
        builder.setHeader("Content-Type", "application/json");
        builder.setTimeoutMillis(REQUEST_TIMEOUT_MS);
        
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
                                // Remember the conversation id for follow-up messages
                                JSONValue sid = jsonObj.get("session_id");
                                if (sid != null && sid.isString() != null) {
                                    setSessionId(sid.isString().stringValue());
                                }
                                
                                JSONValue successValue = jsonObj.get("success");
                                boolean success = successValue != null && successValue.isBoolean() != null
                                        && successValue.isBoolean().booleanValue();
                                
                                if (success) {
                                    JSONValue responseValue = jsonObj.get("response");
                                    String responseText = (responseValue != null && responseValue.isString() != null)
                                            ? formatMarkdown(responseValue.isString().stringValue())
                                            : "No response received";
                                    
                                    // Check if circuit text is available
                                    JSONValue circuitValue = jsonObj.get("circuit_text");
                                    if (circuitValue != null && circuitValue.isString() != null) {
                                        lastCircuitText = circuitValue.isString().stringValue();
                                        importButton.setEnabled(true);
                                        responseText += CIRCUIT_HINT;
                                    }
                                    
                                    addMessageToChat("AI Assistant", responseText, true);
                                } else {
                                    JSONValue errorValue = jsonObj.get("error");
                                    String errorMsg = (errorValue != null && errorValue.isString() != null)
                                            ? errorValue.isString().stringValue() : "Unknown error";
                                    addMessageToChat("AI Assistant", "Error: " + escapeHtml(errorMsg), true);
                                }
                            }
                        } catch (Exception e) {
                            addMessageToChat("AI Assistant", "Error parsing response: " + escapeHtml(String.valueOf(e.getMessage())), true);
                        }
                    } else {
                        addMessageToChat("AI Assistant", "Server error (HTTP " + response.getStatusCode() + "). Make sure the circuit agent server is running on port 5000.", true);
                    }
                }
                
                public void onError(Request request, Throwable exception) {
                    // Remove loading message
                    removeLastMessage();
                    
                    sendButton.setEnabled(true);
                    isWaitingForResponse = false;
                    
                    addMessageToChat("AI Assistant", 
                        "Connection error: " + escapeHtml(String.valueOf(exception.getMessage())) + 
                        "<br/><br/>Please ensure the circuit agent server is running:<br/>" +
                        "1. Navigate to the 'add' directory<br/>" +
                        "2. Run: python app.py<br/>" +
                        "3. Server should be accessible at " + RAG_API_URL, true);
                }
            });
        } catch (RequestException e) {
            // Remove loading message
            removeLastMessage();
            
            sendButton.setEnabled(true);
            isWaitingForResponse = false;
            
            addMessageToChat("AI Assistant", "Failed to send request: " + escapeHtml(String.valueOf(e.getMessage())), true);
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
    
    // Model/server text is inserted into an HTML widget, so escape it and
    // keep line breaks readable.
    private String escapeHtml(String text) {
        return SafeHtmlUtils.htmlEscape(text).replace("\n", "<br/>");
    }
    
    // Minimal markdown -> HTML for model replies: **bold**, `code`, # headings,
    // numbered and bulleted lists, and blank-line spacing. The text is
    // HTML-escaped first, so nothing the model sends can inject markup.
    private String formatMarkdown(String text) {
        String[] lines = SafeHtmlUtils.htmlEscape(text.replace("\r", "")).split("\n");
        StringBuilder out = new StringBuilder();
        String openList = null;   // "ol", "ul" or null
        
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i];
            String listType = null;
            String content = line;
            String number = null;
            
            if (line.matches("^\\s*\\d+[.)]\\s+.*")) {
                listType = "ol";
                number = line.replaceFirst("^\\s*(\\d+)[.)]\\s+.*$", "$1");
                content = line.replaceFirst("^\\s*\\d+[.)]\\s+", "");
            } else if (line.matches("^\\s*[-*\u2022]\\s+.*")) {
                listType = "ul";
                content = line.replaceFirst("^\\s*[-*\u2022]\\s+", "");
            }
            
            if (listType != null) {
                if (openList != null && !openList.equals(listType)) {
                    out.append("</" + openList + ">");
                    openList = null;
                }
                if (openList == null) {
                    out.append("<" + listType + " style='margin:4px 0;padding-left:24px'>");
                    openList = listType;
                }
                out.append(number != null ? "<li value='" + number + "'>" : "<li>");
                out.append(inlineFormat(content)).append("</li>");
                continue;
            }
            
            if (openList != null) {
                out.append("</" + openList + ">");
                openList = null;
            }
            
            if (line.trim().isEmpty()) {
                out.append("<div style='height:6px'></div>");
            } else if (line.matches("^\\s*#{1,6}\\s+.*")) {
                out.append("<b>").append(inlineFormat(line.replaceFirst("^\\s*#{1,6}\\s+", ""))).append("</b><br/>");
            } else {
                out.append(inlineFormat(line)).append("<br/>");
            }
        }
        if (openList != null) {
            out.append("</" + openList + ">");
        }
        
        String html = out.toString();
        if (html.endsWith("<br/>")) {
            html = html.substring(0, html.length() - 5);
        }
        return html;
    }
    
    private String inlineFormat(String s) {
        return s.replaceAll("\\*\\*(.+?)\\*\\*", "<b>$1</b>")
                .replaceAll("`([^`]+)`", "<code>$1</code>");
    }
    
    // Fetch the saved transcript for this session and redraw it in the chat.
    private void loadHistory() {
        String url = RAG_API_URL + "/history/" + URL.encodePathSegment(sessionId);
        RequestBuilder builder = new RequestBuilder(RequestBuilder.GET, url);
        builder.setTimeoutMillis(10000);
        
        try {
            builder.sendRequest(null, new RequestCallback() {
                public void onResponseReceived(Request request, Response response) {
                    if (response.getStatusCode() != 200) {
                        return;
                    }
                    try {
                        JSONObject obj = JSONParser.parseStrict(response.getText()).isObject();
                        if (obj == null || obj.get("messages") == null) {
                            return;
                        }
                        JSONArray msgs = obj.get("messages").isArray();
                        if (msgs == null) {
                            return;
                        }
                        
                        String lastCircuit = null;
                        for (int i = 0; i < msgs.size(); i++) {
                            JSONObject m = msgs.get(i).isObject();
                            if (m == null) {
                                continue;
                            }
                            String role = strField(m, "role");
                            String text = strField(m, "text");
                            if (text == null) {
                                continue;
                            }
                            if ("user".equals(role)) {
                                addMessageToChat("You", escapeHtml(text), false);
                            } else {
                                String html = formatMarkdown(text);
                                String circuit = strField(m, "circuit");
                                if (circuit != null) {
                                    html += CIRCUIT_HINT;
                                    lastCircuit = circuit;
                                }
                                addMessageToChat("AI Assistant", html, true);
                            }
                        }
                        
                        if (lastCircuit != null) {
                            lastCircuitText = lastCircuit;
                            importButton.setEnabled(true);
                        }
                    } catch (Exception e) {
                        // History is a convenience; ignore anything malformed.
                    }
                }
                
                public void onError(Request request, Throwable exception) {
                    // Server not reachable: just start with an empty chat.
                }
            });
        } catch (RequestException e) {
            // ignore
        }
    }
    
    private String strField(JSONObject o, String key) {
        JSONValue v = o.get(key);
        return (v != null && v.isString() != null) ? v.isString().stringValue() : null;
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
        setSessionId(null);   // start a fresh agent conversation
        importButton.setEnabled(false);
        addMessageToChat("AI Assistant", "Chat cleared. How can I help you?", true);
    }
}