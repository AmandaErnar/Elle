
// script.js

// State variables (global for simplicity in plain JS)
let turbineData = {
    windSpeed: 'N/A',
    windDirection: 'N/A',
    currentPower: 'N/A',
    totalEnergy: 'N/A', // This is not in user's HTML, but kept for completeness
    generatorTemp: 'N/A',
    batteryTemp: 'N/A',
    status: 'Offline',
};

let agricultureInsights = 'No insights yet.';
let chatHistory = [];
let isLoading = false; // For chatbot loading state

// DOM elements
const windSpeedEl = document.getElementById('windspeed');
const windDirectionEl = document.getElementById('winddirection');
const currentPowerEl = document.getElementById('currentpower');
// const totalEnergyEl = document.getElementById('total-energy'); // Not in user's HTML
const generatorTempEl = document.getElementById('generatortemperature');
const batteryTempEl = document.getElementById('batterytemperature');
const statusDisplayEl = document.getElementById('turbinestatus');
const agricultureInsightsEl = document.getElementById('agricultureinsights');
const chatHistoryEl = document.getElementById('chathistory');
const chatInputEl = document.getElementById('chatinput');
const chatFormEl = document.getElementById('chatbotform');
const sendButtonEl = document.getElementById('sendbutton');
const currentYearEl = document.getElementById('current-year'); // This ID was from my previous HTML, will need to be added to user's HTML if they want it.

// Helper function to determine status color class
const getStatusColorClass = (status) => {
    switch (status) {
        case 'Operational':
            return 'status-operational'; // Custom class for CSS
        case 'Warning':
            return 'status-warning';     // Custom class for CSS
        case 'Error':
            return 'status-error';       // Custom class for CSS
        default:
            return ''; // No specific class for default/offline, relies on base CSS
    }
};

// Function to update the UI with current data
const updateUI = () => {
    windSpeedEl.textContent = turbineData.windSpeed;
    windDirectionEl.textContent = turbineData.windDirection;
    currentPowerEl.textContent = turbineData.currentPower;
    // if (totalEnergyEl) { // Check if element exists before updating
    //     totalEnergyEl.textContent = turbineData.totalEnergy;
    // }

    generatorTempEl.textContent = turbineData.generatorTemp;
    batteryTempEl.textContent = turbineData.batteryTemp;

    // Update status display
    statusDisplayEl.textContent = turbineData.status;
    // Remove previous status classes and add new one
    statusDisplayEl.className = ''; // Clear existing classes
    statusDisplayEl.classList.add(getStatusColorClass(turbineData.status));


    agricultureInsightsEl.textContent = agricultureInsights;

    // Update chat history display
    chatHistoryEl.innerHTML = ''; // Clear existing messages
    if (chatHistory.length === 0) {
        const initialMsg = document.createElement('p');
        initialMsg.className = 'text-gray-500 text-center italic'; // Keeping some simple classes here for clarity
        initialMsg.textContent = 'Type a message to start chatting with Elle!';
        chatHistoryEl.appendChild(initialMsg);
    } else {
        chatHistory.forEach((msg) => {
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message ${msg.role}`; // Use .chat-message.user or .chat-message.bot
            msgDiv.textContent = msg.text;
            chatHistoryEl.appendChild(msgDiv);
        });
    }

    if (isLoading) {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'chat-message typing'; // Use .chat-message.typing
        loadingDiv.textContent = 'Elle is typing...';
        chatHistoryEl.appendChild(loadingDiv);
    }
    // Scroll to bottom of chat history
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
};

// Function to simulate fetching data from a backend
const fetchData = async () => {
    try {
        // Mock data for demonstration purposes
        const mockData = {
            windSpeed: (Math.random() * 20).toFixed(1) + ' m/s',
            windDirection: ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.floor(Math.random() * 8)],
            currentPower: (Math.random() * 500).toFixed(2) + ' W',
            // totalEnergy: (Math.random() * 1000).toFixed(2) + ' kWh', // Not in user's HTML
            generatorTemp: (20 + Math.random() * 15).toFixed(1) + '°C',
            batteryTemp: (25 + Math.random() * 10).toFixed(1) + '°C',
            status: Math.random() > 0.8 ? 'Warning' : 'Operational',
        };

        turbineData = mockData;

        // Simulate AI agriculture insights
        agricultureInsights = Math.random() > 0.5
            ? 'Optimal time for irrigation based on energy surplus.'
            : 'Consider delaying heavy machinery use; low wind forecast.';

    } catch (error) {
        console.error("Failed to fetch turbine data:", error);
        turbineData.status = 'Error';
    } finally {
        updateUI(); // Always update UI after data fetch attempt
    }
};

// Function to handle chatbot message sending
const handleChatSubmit = async (e) => {
    e.preventDefault();
    const message = chatInputEl.value.trim();
    if (!message) return;

    const userMessage = { role: 'user', text: message };
    chatHistory.push(userMessage);
    chatInputEl.value = ''; // Clear input
    updateUI(); // Update UI to show user message
    isLoading = true;
    sendButtonEl.disabled = true;
    chatInputEl.disabled = true;
    updateUI(); // Show "Elle is typing..."

    try {
        // LLM API call for demonstration
        const prompt = message;
        let chatHistoryForAPI = [];
        chatHistoryForAPI.push({ role: "user", parts: [{ text: prompt }] });
        const payload = { contents: chatHistoryForAPI };
        const apiKey = ""; // Canvas will automatically provide this in runtime
        const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        let botResponseText = "Sorry, I couldn't get a response right now.";
        if (result.candidates && result.candidates.length > 0 &&
            result.candidates[0].content && result.candidates[0].content.parts &&
            result.candidates[0].content.parts.length > 0) {
            botResponseText = result.candidates[0].content.parts[0].text;
        }

        const botResponse = { role: 'bot', text: botResponseText };
        chatHistory.push(botResponse);

    } catch (error) {
        console.error("Error sending message to chatbot:", error);
        chatHistory.push({ role: 'bot', text: 'Error: Could not connect to the chatbot.' });
    } finally {
        isLoading = false;
        sendButtonEl.disabled = false;
        chatInputEl.disabled = false;
        updateUI(); // Final UI update after bot response or error
    }
};

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if currentYearEl exists before trying to set its textContent
    if (currentYearEl) {
        currentYearEl.textContent = new Date().getFullYear(); // Set current year in footer
    }

    // Set up event listener for the chat form
    chatFormEl.addEventListener('submit', handleChatSubmit);

    // Initial data fetch and then set up interval
    fetchData();
    setInterval(fetchData, 5000); // Fetch data every 5 seconds
});
