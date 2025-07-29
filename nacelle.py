import os
import sys
import json
import time
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt

MQTT_BROBROKER_HOST = ""
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "elle/turbine/"

GEMINI_API_KEY = "AIzaSyCCeiCw5-I108sPwz8NG0UW8_clXDNVuIU" 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

app = Flask(__name__, static_folder='ui', template_folder='ui')
socketio = SocketIO(app, cors_allowed_origins="*") 

latest_sensor_data = {
    "temperature": "N/A",
    "humidity": "N/A",
    "voltage": "N/A",
    "current": "N/A",
    "power": "N/A",
    "timestamp": "N/A"
}
latest_ai_insight = "Receiving insights..."

def on_connect(client, userdata, flags, rc):
    """Callback function when the MQTT client connects to the broker."""
    if rc == 0:
        print(f"MQTT Backend Connected to broker with result code {rc}")
        for topic in ["humidity", "temperature", "voltage", "current", "power"]:
            full_topic = f"{MQTT_TOPIC_BASE}{topic}"
            client.subscribe(full_topic)
            print(f"Subscribed to MQTT topic: {full_topic}")
    else:
        print(f"MQTT Backend Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    global latest_sensor_data

    topic = msg.topic.decode('utf-8')
    payload = msg.payload.decode('utf-8')
    print(f"Received MQTT - Topic: {topic}, Payload: {payload}")

    if topic.startswith(MQTT_TOPIC_BASE):
        sensor_type = topic.replace(MQTT_TOPIC_BASE, "")
        latest_sensor_data[sensor_type] = payload
        latest_sensor_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        socketio.emit('sensor_update', latest_sensor_data)
        print(f"Emitted sensor_update: {latest_sensor_data}")

        trigger_ai_insight_generation()

def generate_ai_insight(data):
    if data["temperature"] == "N/A" or data["humidity"] == "N/A" or \
       data["voltage"] == "N/A" or data["current"] == "N/A" or data["power"] == "N/A":
        return "Not enough data for a comprehensive insight yet. Awaiting all sensor readings."

    prompt = f"""
    You are an AI agricultural assistant. Based on the following sensor readings from a turbine system in an agricultural setting, provide a concise and actionable insight or recommendation. Focus on potential issues, optimal conditions, or areas for improvement related to plant health, energy efficiency, or system maintenance.

    Current Readings:
    - Temperature: {data['temperature']}
    - Humidity: {data['humidity']}
    - Voltage: {data['voltage']}
    - Current: {data['current']}
    - Power: {data['power']}

    Consider typical ranges for agricultural environments (e.g., optimal humidity 50-70%, temperature 20-28°C). If values are outside typical ranges, suggest a specific action. If power readings are unusually low or high, comment on potential energy efficiency or system health.

    Provide only the insight text, no conversational filler.
    """

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 150,
        }
    }

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        api_key_param = f"?key={GEMINI_API_KEY}" if GEMINI_API_KEY else ""
        response = requests.post(f"{GEMINI_API_URL}{api_key_param}", headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        result = response.json()

        if result.get("candidates") and result["candidates"][0].get("content") and \
           result["candidates"][0]["content"].get("parts") and \
           result["candidates"][0]["content"]["parts"][0].get("text"):
            insight = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"Generated AI Insight: {insight}")
            return insight
        else:
            print(f"AI API response missing expected content: {result}")
            return "Failed to generate AI insight: Unexpected API response structure."
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return f"Failed to generate AI insight: API call error ({e})."
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Gemini API: {e}")
        return f"Failed to generate AI insight: Invalid JSON response ({e})."
    except Exception as e:
        print(f"An unexpected error occurred during AI insight generation: {e}")
        return f"Failed to generate AI insight: An unexpected error occurred ({e})."

def trigger_ai_insight_generation():
    """Triggers AI insight generation and updates the frontend."""
    global latest_ai_insight
    new_insight = generate_ai_insight(latest_sensor_data)
    if new_insight != latest_ai_insight: 
        latest_ai_insight = new_insight
        socketio.emit('ai_insight', {'insight': latest_ai_insight})
        print(f"Emitted AI insight: {latest_ai_insight}")

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@socketio.on('connect')
def test_connect():
    """Handles new SocketIO client connections."""
    print('Client connected')
    emit('sensor_update', latest_sensor_data)
    emit('ai_insight', {'insight': latest_ai_insight})

@socketio.on('disconnect')
def test_disconnect():
    """Handles SocketIO client disconnections."""
    print('Client disconnected')

if __name__ == '__main__':
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(MQTT_BROBROKER_HOST, MQTT_PORT, 60)
        mqtt_client.loop_start()

        print(f"Starting Flask server on http://127.0.0.1:5000")
        socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nBackend shutting down gracefully...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            print("MQTT client disconnected.")
        print("Backend shutdown complete.")

