# Scout Sensor Map

Scout Sensor Map is a receiving side of SCOUT data. It also provides a webpage with map
that shows the data received from SCOUT. Only one map can be opened at a time since we
don't multiplex the data.

## How to point your SCOUT to local Sensor Map

- Get the IP address of your local machine (linux: `ip a`, windows: `ifconfig`)
- Start this app as `scout-sensor-demo-map --http-port 9090`
- In your web browser, go to `http://<scout-ip>:8080`
    - Add a custom forwarder in the SCOUT UI as `http://<your-ip>:9090/odid` (click Save)
    - Add heartbeat in the SCOUT UI as `http://<your-ip>:9090/heartbeat` (click Save)
    - You can close the Scout UI now
- In your web browser, go to `localhost:9090`. The map should report connected and receive at least a heartbeat


## Installation

Open your terminal. Make sure to have python3 installed (try `python --version` - should report
version greater than 3.9). Make sure to have `pip` also installed.

### Using virtualenv

We recommend using virtualenv - separate python packages installation folder from the system folder.
Open terminal, go to the location where you want to have the virtual env. Create one
`python -m venv my-virtualenv`. Switch to it linux: `source my-virtualenv/bin/activate`; windows `my-virtualenv\Scripts\Activate.ps1`. Now you have fresh python evironment separate from the system.
Every time you want to use this virtual environment, you need to activate it. For Windows user,
you might need to change scripts execution policy to run the Activate.ps1 by `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser`


`pip install scout_sensor_demo_map-<version>.tar.gz`


## Usage

`scout-sensor-demo-map`
