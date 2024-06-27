# Husqvarna Mower Control System

## Overview

The Husqvarna Mower Control System is a Python-based project designed to control Husqvarna robotic mowers based on weather conditions and specific operating hours. This system integrates with the Husqvarna API to manage mower operations, ensuring the mower only runs when conditions are optimal.

## Configuration

Before running the application, you need to configure the following variables in the `mower_control.py` file:

### Husqvarna API Credentials

- **HUSQVARNA_APPLICATION_KEY**: Your Husqvarna application key.
- **HUSQVARNA_APPLICATION_SECRET**: Your Husqvarna application secret.

```python
HUSQVARNA_APPLICATION_KEY = 'your-application-key'
HUSQVARNA_APPLICATION_SECRET = 'your-application-secret'
```
Location Coordinates
Set the latitude and longitude for your location.
```python
LOCATION = {'lat': your_latitude, 'lon': your_longitude}

```
Local Time Zone

Update the time zone to match your local time zone. This is used for controlling the mower's operating hours.
```python
local_tz = pytz.timezone('Your/LocalTimezone')
