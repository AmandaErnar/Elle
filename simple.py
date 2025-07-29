import network
import time
import machine
from umqtt.simple import MQTTClient
import ubinascii

WIFI_SSID = " "
WIFI_PASSWORD = " "


MQTT_BROKER = " "
MQTT_PORT = 1883

CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
MQTT_CLIENT_ID = f"elle_pico_w_{CLIENT_ID}"

MQTT_TOPIC_BASE = b"elle/turbine/"

TOPICS = {
    "humidity": MQTT_TOPIC_BASE + b"humidity",
    "temperature": MQTT_TOPIC_BASE + b"temperature",
    "voltage": MQTT_TOPIC_BASE + b"voltage",
    "current": MQTT_TOPIC_BASE + b"current",
    "power": MQTT_TOPIC_BASE + b"power"
}

I2C_SDA_PIN = machine.Pin(0)
I2C_SCL_PIN = machine.Pin(1)
I2C_BUS_ID = 0

HDC3022_I2C_ADDR = 0x44
INA260_I2C_ADDR = 0x40

INA260_REG_CONFIG = 0x00
INA260_REG_VOLTAGE = 0x01
INA260_REG_POWER = 0x03
INA260_REG_CURRENT = 0x04

led = machine.Pin(17, machine.Pin.OUT)

BUTTON_PIN = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)

i2c = None

def button_pressed_handler(pin):
    time.sleep_ms(50)
    if pin.value() == 0:
        print("button pressed! resetting...")
        machine.reset()

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    time.sleep(1)

    print(f"connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    max_attempts = 20
    attempts = 0
    led.value(1)

    while wlan.status() != 3 and attempts < max_attempts:
        led.toggle()
        print(f"attempt {attempts+1}/{max_attempts}: status={wlan.status()}")
        time.sleep(0.5)
        attempts += 1

    if wlan.status() == 3:
        led.value(0)
        print("WiFi connected.")
        print("IP address:", wlan.ifconfig()[0])
        return True
    else:
        led.value(0)
        print(f"failed to connect. status code: {wlan.status()}")
        return False

def connect_mqtt():
    print(f"connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        client.connect()
        print("connected to MQTT broker successfully!")
        return client
    except Exception as e:
        print(f"failed to connect to MQTT broker: {e}")
        return None

def connect_sensors():
    global i2c
    print("initializing I2C bus, scanning for sensors...")
    try:
        i2c = machine.I2C(I2C_BUS_ID, sda=I2C_SDA_PIN, scl=I2C_SCL_PIN, freq=400000)
        print("I2C initialized.")
        time.sleep(1)
        devices = i2c.scan()
        if devices:
            print("I2C devices found at these addresses:", [hex(d) for d in devices])
        else:
            print("no I2C devices found; check wiring!")
            return False

        ina260_present = False
        if INA260_I2C_ADDR in devices:
            print(f"INA260 (0x{INA260_I2C_ADDR:x}) detected. configuring now...")
            i2c.writeto(INA260_I2C_ADDR, bytearray([INA260_REG_CONFIG, 0x61, 0x80]))
            print("INA260 configured.")
            ina260_present = True
        else:
            print(f"INA260 (0x{INA260_I2C_ADDR:x}) not found on I2C bus; please check wiring and address!")

        hdc3022_present = False
        if HDC3022_I2C_ADDR in devices:
            print(f"HDC3022 (0x{HDC3022_I2C_ADDR:x}) detected.")
            hdc3022_present = True
        else:
            print(f"HDC3022 (0x{HDC3022_I2C_ADDR:x}) not found on I2C bus; please check wiring and address!")

        if ina260_present and hdc3022_present:
            print("all required sensors detected and initialized.")
            return True
        else:
            print("1 or more required sensors not detected; please check wiring and addresses!")
            return False

    except Exception as e:
        print(f"error initializing I2C or sensors: {e}")
        return False


def read_hdc3022():
    temp_c = "N/A"
    humidity = "N/A"
    if i2c is None:
        print("HDC3022: I2C bus not initialized.")
        return temp_c, humidity

    print("reading from HDC3022 sensor...")
    try:
        i2c.writeto(HDC3022_I2C_ADDR, bytearray([0x2C, 0x06]))
        time.sleep_ms(20)

        data = i2c.readfrom(HDC3022_I2C_ADDR, 6)

        raw_temp = (data[0] << 8) | data[1]
        temp_c = (raw_temp / 65535.0) * 175.0 - 45.0
        temp_c_str = f"{temp_c:.1f}°C"

        raw_humidity = (data[3] << 8) | data[4]
        humidity = (raw_humidity / 65535.0) * 100.0
        humidity_str = f"{humidity:.1f}%"

        print(f"HDC3022: TEMPERATURE={temp_c_str}, HUMIDITY={humidity_str}")
        return temp_c_str, humidity_str

    except Exception as e:
        print(f"error reading HDC3022: {e}")
    return temp_c, humidity

def read_ina260():
    voltage = "N/A"
    current = "N/A"
    power = "N/A"
    if i2c is None:
        print("INA260: I2C bus not initialized!")
        return voltage, current, power

    print("reading from INA260 sensor...")
    try:
        i2c.writeto(INA260_I2C_ADDR, bytearray([INA260_REG_VOLTAGE]))
        raw_voltage = i2c.readfrom(INA260_I2C_ADDR, 2)
        voltage_val = int.from_bytes(raw_voltage, 'big')
        voltage = voltage_val * 1.25 / 1000
        voltage_str = f"{voltage:.2f}V"

        i2c.writeto(INA260_I2C_ADDR, bytearray([INA260_REG_CURRENT]))
        raw_current = i2c.readfrom(INA260_I2C_ADDR, 2)
        current_val = int.from_bytes(raw_current, 'big')
        if current_val & 0x8000:
            current_val -= 0x10000
        current = current_val * 1.25 / 1000
        current_str = f"{current:.2f}A"

        i2c.writeto(INA260_I2C_ADDR, bytearray([INA260_REG_POWER]))
        raw_power = i2c.readfrom(INA260_I2C_ADDR, 2)
        power_val = int.from_bytes(raw_power, 'big')
        power = power_val * 10 / 1000
        power_str = f"{power:.2f}W"

        print(f"INA260: VOLTAGE={voltage_str}, CURRENT={current_str}, POWER={power_str}")
        return voltage_str, current_str, power_str

    except Exception as e:
        print(f"error reading INA260: {e}")
    return voltage, current, power

def main():
    print(f"\n starting  Elle Pico W client: {MQTT_CLIENT_ID}")

    BUTTON_PIN.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_pressed_handler)

    if not connect_wifi():
        print("exiting due to WiFi connection failure.")
        return

    if not connect_sensors():
        print("exiting due to sensor connection/initialization failure.")
        return

    mqtt_client = None
    while mqtt_client is None:
        mqtt_client = connect_mqtt()
        if mqtt_client is None:
            print("retrying MQTT connection in 5 seconds...")
            time.sleep(5)

    print("\n executing the main data collection loop")
    while True:
        print(f"\n reading sensors at {time.time()}")
        temp_c, humidity = read_hdc3022()

        voltage, current, power = read_ina260()

        print("publishing data to MQTT...")
        try:
            if mqtt_client:
                mqtt_client.publish(TOPICS["temperature"], str(temp_c).encode())
                mqtt_client.publish(TOPICS["humidity"], str(humidity).encode())
                mqtt_client.publish(TOPICS["voltage"], str(voltage).encode())
                mqtt_client.publish(TOPICS["current"], str(current).encode())
                mqtt_client.publish(TOPICS["power"], str(power).encode())
                print(f"data publication successful: T={temp_c}, H={humidity}, V={voltage}, A={current}, P={power}")
            else:
                print("MQTT client not connected! reconnecting...")
                mqtt_client = connect_mqtt()
        except Exception as e:
            print(f"error publishing data! {e}. resetting MQTT client and reconnecting...")
            mqtt_client = None

        time.sleep(5)
        print("NEXT READING IN FIVE SECONDS!!!")

if __name__ == "__main__":
    main()
