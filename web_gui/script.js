console.log('Script.js loaded and executing!');
// CEC Test Tool Web Interface
document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const powerOnBtn = document.getElementById('powerOnBtn');
    const powerOffBtn = document.getElementById('powerOffBtn');
    const scanBtn = document.getElementById('scanBtn');
    const statusBtn = document.getElementById('statusBtn');
    const sendCommandBtn = document.getElementById('sendCommandBtn');
    const customCommandInput = document.getElementById('customCommand');
    const statusOutput = document.getElementById('statusOutput');
    
    // API endpoints
    const API_ENDPOINTS = {
        powerOn: '/api/power/on',
        powerOff: '/api/power/off',
        scan: '/api/scan',
        status: '/api/status',
        command: '/api/command'
    };
    
    // Helper function to update status output
    function updateStatus(message, isError = false) {
        const timestamp = new Date().toLocaleTimeString();
        const formattedMessage = `[${timestamp}] ${message}`;
        
        if (isError) {
            statusOutput.innerHTML += `<div class="error">${formattedMessage}</div>`;
        } else {
            statusOutput.innerHTML += `<div>${formattedMessage}</div>`;
        }
        
        // Auto-scroll to bottom
        statusOutput.scrollTop = statusOutput.scrollHeight;
    }
    
    // Helper function to make API requests
    async function makeRequest(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            updateStatus(`Sending request to ${endpoint}...`);
            const response = await fetch(endpoint, options);
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            updateStatus(`Error: ${error.message}`, true);
            return null;
        }
    }
    
    // Event listeners for buttons
    powerOnBtn.addEventListener('click', async function() {
        const result = await makeRequest(API_ENDPOINTS.powerOn, 'POST');
        if (result) {
            updateStatus('Power ON command sent.');
            updateStatus(result.result);
        }
    });
    
    powerOffBtn.addEventListener('click', async function() {
        const result = await makeRequest(API_ENDPOINTS.powerOff, 'POST');
        if (result) {
            updateStatus('Power OFF command sent.');
            updateStatus(result.result);
        }
    });
    
    scanBtn.addEventListener('click', async function() {
        const result = await makeRequest(API_ENDPOINTS.scan);
        if (result) {
            updateStatus('Scan completed:');
            updateStatus(result.result);
        }
    });
    
    statusBtn.addEventListener('click', async function() {
        const result = await makeRequest(API_ENDPOINTS.status);
        if (result) {
            updateStatus('Status check completed:');
            updateStatus(result.result);
        }
    });
    
    sendCommandBtn.addEventListener('click', async function() {
        const command = customCommandInput.value.trim();
        if (!command) {
            updateStatus('Please enter a command.', true);
            return;
        }
        
        const result = await makeRequest(API_ENDPOINTS.command, 'POST', { command });
        if (result) {
            updateStatus(`Command sent: ${command}`);
            updateStatus(result.result);
        }
        
        // Clear the input field after sending the command
        customCommandInput.value = '';
    });
    
    // Allow pressing Enter to send a custom command
    customCommandInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendCommandBtn.click();
        }
    });
    
    // Initial scan on page load
    setTimeout(async function() {
        updateStatus('CEC Test Tool initialized. Scanning for devices...');
        await scanBtn.click();
    }, 1000);
});
