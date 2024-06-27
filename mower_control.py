import requests
import schedule
import time
from datetime import datetime, timedelta, timezone
import pytz

# Constants
HUSQVARNA_APPLICATION_KEY = 'YOUR_API_KEY'
HUSQVARNA_APPLICATION_SECRET = 'YOUR_API_SECRET'
LOCATION = {'lat': -0.0, 'lon': 0.0} # SET YOUR LONG/LAT
RAIN_WEATHER_CODES = [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 80, 81, 82, 95, 96,
                      99]  # Rain, snow, hail codes from Open-Meteo

# Mapping of weather codes to descriptions and rain intensity
WEATHER_DESCRIPTIONS = {
    0: ('Clear sky', 'Dry'),
    1: ('Mainly clear', 'Dry'),
    2: ('Partly cloudy', 'Dry'),
    3: ('Overcast', 'Dry'),
    45: ('Fog', 'Dry'),
    51: ('Drizzle (light)', 'Slight'),
    53: ('Drizzle (moderate)', 'Moderate'),
    55: ('Drizzle (dense)', 'Heavy'),
    56: ('Freezing drizzle (light)', 'Slight'),
    57: ('Freezing drizzle (dense)', 'Heavy'),
    61: ('Rain (slight)', 'Moderate'),
    63: ('Rain (moderate)', 'Heavy'),
    65: ('Rain (heavy)', 'Very Heavy'),
    66: ('Freezing rain (slight)', 'Moderate'),
    67: ('Freezing rain (heavy)', 'Very Heavy'),
    71: ('Snow fall (slight)', 'Moderate'),
    73: ('Snow fall (moderate)', 'Heavy'),
    75: ('Snow fall (heavy)', 'Very Heavy'),
    80: ('Rain showers (slight)', 'Moderate'),
    81: ('Rain showers (moderate)', 'Heavy'),
    82: ('Rain showers (violent)', 'Very Heavy'),
    95: ('Thunderstorm (slight or moderate)', 'Heavy'),
    96: ('Thunderstorm with slight hail', 'Moderate'),
    99: ('Thunderstorm with heavy hail', 'Very Heavy')
}

# Rain intensity to weight mapping
RAIN_INTENSITY_WEIGHTS = {
    'Slight': 0.75,
    'Moderate': 0.5,
    'Heavy': 0.25,
    'Very Heavy': 0.1
}


class MowerControl:
    def __init__(self):
        self.access_token = self.authenticate()
        self.mower_ids = self.get_mower_ids()
        self.past_weather = None
        self.current_weather = None
        self.forecast_weather = None
        self.good_weather = None
        self.currently_raining = None
        self.forecast_analysis = None


    def authenticate(self):
        print("Authenticating with Husqvarna API...")
        url = 'https://api.authentication.husqvarnagroup.dev/v1/oauth2/token'
        data = {
            'grant_type': 'client_credentials',
            'client_id': HUSQVARNA_APPLICATION_KEY,
            'client_secret': HUSQVARNA_APPLICATION_SECRET,
            'scope': 'amc:api'
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        print("Authentication successful.")
        return response_data['access_token']

    def get_mower_ids(self):
        print("Fetching mower IDs...")
        url = 'https://api.amc.husqvarna.dev/v1/mowers'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Authorization-Provider': 'husqvarna',
            'X-Api-Key': HUSQVARNA_APPLICATION_KEY
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        mowers = response.json()['data']
        mower_ids = [mower['id'] for mower in mowers]
        print(f"Fetched mower IDs: {mower_ids}")
        return mower_ids

    def get_past_weather(self):
        print("Fetching past weather data...")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=48)

        start_time_str = start_time.strftime('%Y-%m-%d')
        end_time_str = end_time.strftime('%Y-%m-%d')

        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={LOCATION['lat']}&longitude={LOCATION['lon']}"
               f"&start_date={start_time_str}&end_date={end_time_str}"
               "&hourly=weathercode")

        response = requests.get(url)
        response.raise_for_status()
        print("Fetched past weather data.")

        data = response.json()
        local_tz = pytz.timezone('Your/LocalTimezone')  # Change to your local time zone

        # Filter out future timestamps and include local time, description, and intensity
        hourly_data = {'time': [], 'weathercode': [], 'local_time': [], 'description': [], 'intensity': []}
        for i, time_str in enumerate(data['hourly']['time']):
            time_obj = datetime.strptime(time_str, '%Y-%m-%dT%H:%M').replace(tzinfo=pytz.utc)
            if time_obj <= datetime.now(timezone.utc):
                local_time = time_obj.astimezone(local_tz).strftime('%d %B %I:%M %p')
                weather_code = data['hourly']['weathercode'][i]
                description, intensity = WEATHER_DESCRIPTIONS.get(weather_code, ('Unknown', 'Dry'))
                hourly_data['time'].append(time_str)
                hourly_data['weathercode'].append(weather_code)
                hourly_data['local_time'].append(local_time)
                hourly_data['description'].append(description)
                hourly_data['intensity'].append(intensity)

        return hourly_data

    def has_been_good_weather(self, past_weather):
        print("Analyzing weather data for the past 48 hours...")
        weather_codes = past_weather['weathercode']
        timestamps = past_weather['time']
        total_hours = len(weather_codes)
        weighted_score = 0

        print(
            f"{'UTC Time':<20} {'Local Time':<20} {'Weather Code':<15} {'Description':<30} {'Intensity':<15} {'Weight':<10} {'Good Weather':<15}")
        print("-" * 150)

        local_tz = pytz.timezone('Your/LocalTimezone')  # Change to your local time zone

        for i, code in enumerate(weather_codes):
            # Adjust weight so that the newest data has the highest weight
            weight = (i + 1) / total_hours
            description, intensity = WEATHER_DESCRIPTIONS.get(code, ('Unknown', 'Dry'))
            good_weather = intensity == 'Dry'
            if not good_weather:
                weight *= RAIN_INTENSITY_WEIGHTS.get(intensity, 1)
            weighted_score += weight if good_weather else -weight

            # Convert UTC timestamp to local time
            utc_time = datetime.strptime(timestamps[i], '%Y-%m-%dT%H:%M').replace(tzinfo=pytz.utc)
            local_time = utc_time.astimezone(local_tz).strftime('%Y-%m-%d %H:%M:%S')
            utc_time_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')

            print(
                f"{utc_time_str:<20} {local_time:<20} {code:<15} {description:<30} {intensity:<15} {weight:<10.2f} {good_weather}")

        max_score = sum((i + 1) / total_hours for i in range(total_hours))
        result = weighted_score / max_score > 0.75
        print(f"Good weather score: {weighted_score:.2f}/{max_score:.2f} ({weighted_score / max_score:.2f})")
        return result

    def get_current_weather(self):
        print("Fetching current weather data...")
        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={LOCATION['lat']}&longitude={LOCATION['lon']}"
               "&current_weather=true")
        response = requests.get(url)
        response.raise_for_status()
        print("Fetched current weather data.")
        current_weather = response.json()

        # Get the weather code from the current weather
        weather_code = current_weather['current_weather']['weathercode']
        description, _ = WEATHER_DESCRIPTIONS.get(weather_code, ('Unknown', 'Dry'))
        current_weather['current_weather']['weather_description'] = description

        return current_weather

    def analyze_forecast_weather(self, forecast_weather):
        print("Analyzing forecasted weather data for the next 24 hours...")
        weather_codes = forecast_weather['hourly']['weathercode']
        timestamps = forecast_weather['hourly']['time']
        total_hours = len(weather_codes)
        forecast_analysis = []

        local_tz = pytz.timezone('Your/LocalTimezone')  # Change to your local time zone
        current_time = datetime.now(timezone.utc)

        for i, code in enumerate(weather_codes):
            utc_time = datetime.strptime(timestamps[i], '%Y-%m-%dT%H:%M').replace(tzinfo=pytz.utc)
            if utc_time > current_time:
                # Adjust weight so that the nearest forecast has the highest weight
                weight = (total_hours - i) / total_hours
                description, intensity = WEATHER_DESCRIPTIONS.get(code, ('Unknown', 'Dry'))
                good_weather = intensity == 'Dry'
                if not good_weather:
                    weight *= RAIN_INTENSITY_WEIGHTS.get(intensity, 1)

                local_time = utc_time.astimezone(local_tz).strftime('%d %B %I:%M %p')
                utc_time_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')

                action = "Resume" if good_weather and (9 <= utc_time.astimezone(local_tz).hour < 17) else "Pause"
                if not (9 <= utc_time.astimezone(local_tz).hour < 17):
                    action = "Time"

                forecast_analysis.append({
                    "utc_time": utc_time_str,
                    "local_time": local_time,
                    "weather_code": code,
                    "description": description,
                    "intensity": intensity,
                    "weight": weight,
                    "good_weather": good_weather,
                    "action": action
                })

        return forecast_analysis

    def is_currently_raining(self, current_weather):
        weather_code = current_weather['current_weather']['weathercode']
        result = weather_code in RAIN_WEATHER_CODES
        print(f"Currently raining: {result}")
        return result

    def resume_mower_schedule(self, mower_id):
        print(f"Resuming schedule for mower {mower_id}...")
        url = f'https://api.amc.husqvarna.dev/v1/mowers/{mower_id}/actions'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/vnd.api+json',
            'Authorization-Provider': 'husqvarna',
            'X-Api-Key': HUSQVARNA_APPLICATION_KEY
        }
        data = {
            'data': {
                'type': 'ResumeSchedule'
            }
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Mower {mower_id} resumed schedule.")

    def park_mower(self, mower_id):
        print(f"Parking mower {mower_id}...")
        url = f'https://api.amc.husqvarna.dev/v1/mowers/{mower_id}/actions'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/vnd.api+json',
            'Authorization-Provider': 'husqvarna',
            'X-Api-Key': HUSQVARNA_APPLICATION_KEY
        }
        data = {
            'data': {
                'type': 'ParkUntilFurtherNotice'
            }
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"Mower {mower_id} parked.")

    def control_mower_based_on_weather(self):
        try:
            print("Starting control process...")
            self.past_weather = self.get_past_weather()
            self.current_weather = self.get_current_weather()
            self.forecast_weather = self.get_weather_forecast()

            self.currently_raining = self.is_currently_raining(self.current_weather)
            self.good_weather = self.has_been_good_weather(self.past_weather)
            self.forecast_analysis = self.analyze_forecast_weather(self.forecast_weather)

            # Get current local time
            local_tz = pytz.timezone('Your/LocalTimezone')  # Change to your local time zone
            current_time = datetime.now(local_tz)
            current_hour = current_time.hour

            # Check if current time is between 9 AM and 5 PM
            if 9 <= current_hour < 17:
                if self.currently_raining:
                    self.current_action = "Rain"
                    for mower_id in self.mower_ids:
                        self.park_mower(mower_id)
                elif self.good_weather:
                    self.current_action = "Resume"
                    for mower_id in self.mower_ids:
                        self.resume_mower_schedule(mower_id)
                else:
                    self.current_action = "Weather"
                    for mower_id in self.mower_ids:
                        self.park_mower(mower_id)
            else:
                self.current_action = "Time"
                for mower_id in self.mower_ids:
                    self.park_mower(mower_id)

            print("Control process completed.")
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            print(f"Response content: {http_err.response.content.decode()}")
        except Exception as err:
            print(f"Other error occurred: {err}")

    def run_scheduler(self):
        # Schedule the job to run every 30 minutes
        schedule.every().hour.at(":00").do(self.control_mower_based_on_weather)
        schedule.every().hour.at(":30").do(self.control_mower_based_on_weather)

        # Run the job once immediately
        self.control_mower_based_on_weather()

        # Run the scheduler
        print("Scheduler started.")
        while True:
            schedule.run_pending()
            time.sleep(1)

    def get_weather_forecast(self):
        print("Fetching weather forecast data...")
        end_time = datetime.now(timezone.utc)
        start_time = end_time + timedelta(hours=24)

        start_time_str = end_time.strftime('%Y-%m-%d')
        end_time_str = start_time.strftime('%Y-%m-%d')

        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={LOCATION['lat']}&longitude={LOCATION['lon']}"
               f"&start_date={start_time_str}&end_date={end_time_str}"
               "&hourly=weathercode")

        response = requests.get(url)
        response.raise_for_status()
        print("Fetched weather forecast data.")

        return response.json()
    def get_mower_details(self):
        print("Fetching mower details...")
        url = 'https://api.amc.husqvarna.dev/v1/mowers'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Authorization-Provider': 'husqvarna',
            'X-Api-Key': HUSQVARNA_APPLICATION_KEY
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        mowers = response.json()['data']
        mower_details = [{'id': mower['id'], 'name': mower['attributes']['system']['name']} for mower in mowers]
        print(f"Fetched mower details: {mower_details}")
        return mower_details

    def get_mower_names(self):
        mower_details = self.get_mower_details()
        mower_names = [mower['name'] for mower in mower_details]
        return mower_names

    def get_status(self):
        past_weather_len = len(self.past_weather['time'])
        forecast_weather_len = len(self.forecast_analysis)
        min_length = min(past_weather_len, forecast_weather_len)

        return {
            "mower_names": self.get_mower_names()[0],
            "good_weather": self.good_weather,
            "currently_raining": self.currently_raining,
            "past_weather": self.past_weather,
            "current_weather": self.current_weather,
            "forecast_analysis": self.forecast_analysis,
            "min_length": min_length
        }
