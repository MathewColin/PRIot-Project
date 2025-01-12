from flask import Flask, request, render_template_string, redirect, url_for
from threading import Thread
from awscrt import io, mqtt, auth
from awsiot import mqtt_connection_builder
import os
import json
import signal

# Flask app setup
app = Flask(__name__)

# List to hold incoming messages
messages = []

# MQTT connection setup
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))

def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed")

def on_message_received(topic, payload, **kwargs):
    global messages
    try:
        # Parse the JSON message
        message_data = json.loads(payload.decode())
        if isinstance(message_data, dict) and "message" in message_data:
            messages.append((topic, message_data["message"]))
        else:
            messages.append((topic, payload.decode()))
    except json.JSONDecodeError:
        messages.append((topic, payload.decode()))
    # Do not trigger a redirect here, let the page refresh on the next render

# MQTT connection global variable
mqtt_connection = None

def shutdown_server():
    print("Shutting down server...")
    os._exit(0)  # Ensures entire process stops

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global mqtt_connection
    if mqtt_connection:
        print("Disconnecting MQTT connection...")
        mqtt_connection.disconnect().result()
    shutdown_server()
    return "Server shutting down..."

@app.route('/', methods=['GET', 'POST'])
def index():
    global mqtt_connection

    if request.method == 'POST':
        action = request.form.get('action')
        topic = request.form.get('topic')
        message = request.form.get('message')

        if action == 'Subscribe':
            mqtt_connection.subscribe(
                topic=topic,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=on_message_received
            )
        elif action == 'Unsubscribe':
            mqtt_connection.unsubscribe(topic=topic)
        elif action == 'Publish':
            payload = json.dumps({"message": message})
            mqtt_connection.publish(
                topic=topic,
                payload=payload,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
        elif action == 'FanOn':
            payload = json.dumps({"message": "Toggle fan"})
            mqtt_connection.publish(
                topic="esp32/fan",
                payload=payload,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )
        elif action == 'LedOn':
            payload = json.dumps({"message": "Toggle LED"})
            mqtt_connection.publish(
                topic="esp32/led",
                payload=payload,
                qos=mqtt.QoS.AT_LEAST_ONCE
            )

        # After posting an action, the page will reload naturally
        return redirect(url_for('index'))

    # Enhanced HTML template with CSS for better styling
    html_template = """
		<!doctype html>
		<html>
			<head>
				<title>MQTT Web Interface</title>
				<style>
					body {
						font-family: Arial, sans-serif;
						margin: 0;
						padding: 0;
						background-color: #f4f4f9;
					}
					header {
						background: #4CAF50;
						color: white;
						padding: 10px 20px;
						text-align: center;
					}
					main {
						margin: 20px;
						padding: 20px;
						background: white;
						border-radius: 8px;
						box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
					}
					h1, h2 {
						color: #333;
					}
					form {
						margin-bottom: 20px;
					}
					label {
						display: block;
						margin: 10px 0 5px;
					}
					input[type="text"] {
						width: 100%;
						padding: 8px;
						margin-bottom: 10px;
						border: 1px solid #ddd;
						border-radius: 4px;
					}
					button {
						background: #4CAF50;
						color: white;
						border: none;
						padding: 10px 15px;
						border-radius: 4px;
						cursor: pointer;
					}
					button:hover {
						background: #45a049;
					}
					ul {
						list-style: none;
						padding: 0;
					}
					li {
						background: #f9f9f9;
						margin: 5px 0;
						padding: 10px;
						border: 1px solid #ddd;
						border-radius: 4px;
					}
					strong {
						color: #4CAF50;
					}
					.refresh-button {
						position: fixed;
						right: 20px;
						bottom: 20px;
						background-color: #ff5722;
						color: white;
						padding: 20px 30px;
						font-size: 18px;
						border: none;
						border-radius: 10px;
						cursor: pointer;
						box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
					}
					.refresh-button:hover {
						background-color: #e64a19;
					}
				</style>
				<script>
					function refreshPage() {
						window.location.reload();
					}
				</script>
			</head>
			<body>
				<header>
					<h1>MQTT Web Interface</h1>
				</header>
				<main>
					<h2>Subscribe/Unsubscribe</h2>
					<form method="post">
						<label for="topic">Topic:</label>
						<input type="text" id="topic" name="topic" required>
						<button type="submit" name="action" value="Subscribe">Subscribe</button>
						<button type="submit" name="action" value="Unsubscribe">Unsubscribe</button>
					</form>

					<h2>Publish</h2>
					<form method="post">
						<label for="topic">Topic:</label>
						<input type="text" id="topic" name="topic" required>
						<label for="message">Message:</label>
						<input type="text" id="message" name="message" required>
						<button type="submit" name="action" value="Publish">Publish</button>
					</form>

					<h2>Predefined Actions</h2>
					<form method="post">
						<button type="submit" name="action" value="FanOn">Toggle Fan</button>
						<button type="submit" name="action" value="LedOn">Toggle LED</button>
					</form>

					<h2>Incoming Messages</h2>
					<ul>
						{% for topic, message in messages %}
						<li><strong>{{ topic }}:</strong> {{ message }}</li>
						{% endfor %}
					</ul>

					<h2>Server Control</h2>
					<form action="/shutdown" method="post">
						<button type="submit">Shutdown Server</button>
					</form>
				</main>

				<!-- Refresh Button -->
				<button class="refresh-button" onclick="refreshPage()">Refresh</button>
			</body>
		</html>
		"""



    return render_template_string(html_template, messages=messages)

def run_flask_app():
    app.run(host='0.0.0.0', port=5000, debug=False)

def main():
    global mqtt_connection

    # Spin up the event loop
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    # Set up the credentials provider
    credentials_provider = auth.AwsCredentialsProvider.new_default_chain(client_bootstrap)

    # Set up the MQTT connection
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint="aaqmksedph6go-ats.iot.eu-central-1.amazonaws.com",
        cert_filepath="./5eec132a6098b0bb2c00c0c72d1949925e3ce5b6ba56a389b047de4b275c7929-certificate.pem.crt",
        pri_key_filepath="./5eec132a6098b0bb2c00c0c72d1949925e3ce5b6ba56a389b047de4b275c7929-private.pem.key   ",
        client_bootstrap=client_bootstrap,
        clean_session=False,
        client_id="Web_Server",
        ca_filepath="./AmazonRootCA1.pem",
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        credentials_provider=credentials_provider
    )

    print("Connecting...")
    connected_future = mqtt_connection.connect()

    # Wait for the connection to complete
    connected_future.result()
    print("Connected!")

    # Start the Flask web server in a separate thread
    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Graceful exit on signal
    def signal_handler(sig, frame):
        print("Received signal to shut down...")
        if mqtt_connection:
            mqtt_connection.disconnect().result()
        shutdown_server()

    signal.signal(signal.SIGINT, signal_handler)

    # Keep the main thread alive
    flask_thread.join()

if __name__ == '__main__':
    main()
