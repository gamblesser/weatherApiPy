import requests
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import json
import time

class Behaviors(Enum):
    POLLING = "polling"
    ON_DEMAND = "on_demand"

@dataclass
class City:
    city_name: str
    lat: float
    lon: float
    weather_data: Dict
    created_datetime: datetime

class WeatherApiValidator:
    def is_valid_parameter(self, param: str) -> bool:
        if not param or not isinstance(param, str) or param.strip() == "":
            raise ValueError("Invalid parameter")
        return True
    
    def is_valid_status_code_response(self, response: requests.Response) -> bool:
        if response.status_code != 200:
            raise ValueError(f"Invalid API response: {response.status_code}")
        return True

class WeatherApi:
    weather_api_cache: List['WeatherApi'] = []
    
    def __init__(self, api_key: str, behavior: Behaviors = Behaviors.ON_DEMAND):
        for cached_api in WeatherApi.weather_api_cache:
            if cached_api.api_key == api_key:
                raise RuntimeError("Api key already exists")
        
        self.api_key = api_key
        self.cities: List[City] = []
        self.validator = WeatherApiValidator()
        self.behavior = behavior
        WeatherApi.weather_api_cache.append(self)
    
    @staticmethod
    def delete_weather_api_cache_obj(weather_api: 'WeatherApi') -> None:
        WeatherApi.weather_api_cache.remove(weather_api)
    
    @property
    def api_key(self) -> str:
        return self._api_key
    
    @api_key.setter
    def api_key(self, value: str):
        self._api_key = value
    
    def get_cities(self) -> List[City]:
        return self.cities
    
    def remove_city_by_name(self, city_name: str) -> None:
        self.cities = [city for city in self.cities if city.city_name != city_name]
    
    def get_city_lon_lat(self, city_name: str) -> Dict[str, float]:
        self.validator.is_valid_parameter(city_name)
        
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            self.validator.is_valid_status_code_response(response)
            
            data = response.json()
            if not data:
                return {}
            
            return {
                "lon": float(data[0]["lon"]),
                "lat": float(data[0]["lat"])
            }
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get coordinates: {e}")
    
    def get_and_cache_weather_city(self, city_name: str) -> Dict:
        self.validator.is_valid_parameter(city_name)
        
        if self.behavior == Behaviors.POLLING:
            self.update_cities_cache()
        
        current_time = datetime.now()
        for city in self.cities:
            time_diff = (current_time - city.created_datetime).total_seconds() / 60
            if city.city_name == city_name and time_diff < 10:
                return city.weather_data
        
        lon_lat = self.get_city_lon_lat(city_name)
        if not lon_lat:
            return {}
        
        lon, lat = lon_lat["lon"], lon_lat["lat"]
        
        # Check if we have recent data for these coordinates
        for city in self.cities:
            time_diff = (current_time - city.created_datetime).total_seconds() / 60
            if (city.city_name == city_name and 
                city.lon == lon and 
                city.lat == lat and 
                time_diff < 10):
                return city.weather_data
        
        weather_data = self._send_request_to_get_weather_city_json(city_name, lat, lon)
        
        if len(self.cities) > 9:
            self.cities.remove(0)

        self.cities.append(City(city_name, lat, lon, weather_data, datetime.now()))
        return weather_data
    
    def _send_request_to_get_weather_city_json(self, city_name: str, lat: float, lon: float) -> Dict:
        self.validator.is_valid_parameter(city_name)
        
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            self.validator.is_valid_status_code_response(response)
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get weather data: {e}")
    
    def update_cities_cache(self) -> None:
        current_time = datetime.now()
        for city in self.cities:
            time_diff = (current_time - city.created_datetime).total_seconds() / 60
            if time_diff > 10:
                weather_data = self._send_request_to_get_weather_city_json(
                    city.city_name, city.lat, city.lon
                )
                city.weather_data = weather_data
                city.created_datetime = current_time

# Example usage:
if __name__ == "__main__":
    api = WeatherApi("bb6ea02118db63bd5e4ba1a032889990", Behaviors.ON_DEMAND)
    weather = api.get_and_cache_weather_city("London")
    print(api.cities)
    api.remove_city_by_name("London")
    print(api.cities)