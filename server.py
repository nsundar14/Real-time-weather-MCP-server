"""
Weather Data MCP Server using Open-Meteo API (Free, No API Key Required)
FastMCP-based server for real-time weather information
"""

from fastmcp import FastMCP
import requests
from typing import Dict, Any
from datetime import datetime

# Initialize FastMCP server
mcp = FastMCP("Weather Data MCP")

# Open-Meteo API base URL (free, no API key required)
BASE_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode_city(city: str) -> Dict[str, Any]:
    """Convert city name to coordinates using Open-Meteo Geocoding API"""
    try:
        params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        
        response = requests.get(GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("results"):
            return {"error": f"City '{city}' not found"}
        
        result = data["results"][0]
        return {
            "name": result.get("name"),
            "latitude": result.get("latitude"),
            "longitude": result.get("longitude"),
            "country": result.get("country"),
            "timezone": result.get("timezone", "UTC")
        }
    except Exception as e:
        return {"error": f"Geocoding failed: {str(e)}"}


@mcp.tool()
def get_current_weather(city: str, temperature_unit: str = "celsius") -> Dict[str, Any]:
    """
    Get current weather data for a specified city.
    
    Args:
        city: City name (e.g., "London", "New York", "Tokyo")
        temperature_unit: Temperature unit - "celsius" or "fahrenheit" (default: "celsius")
    
    Returns:
        Current weather information including temperature, humidity, conditions, etc.
    """
    try:
        # Get city coordinates
        location = geocode_city(city)
        if "error" in location:
            return location
        
        # Determine temperature unit parameter
        temp_unit = "fahrenheit" if temperature_unit.lower() == "fahrenheit" else "celsius"
        
        # Get weather data
        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", 
                       "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m"],
            "temperature_unit": temp_unit,
            "wind_speed_unit": "kmh",
            "timezone": location.get("timezone", "UTC")
        }
        
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        current = data.get("current", {})
        
        # Weather code mapping (simplified)
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Foggy", 51: "Light drizzle", 53: "Moderate drizzle",
            55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
            81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
            96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        
        weather_code = current.get("weather_code", 0)
        weather_description = weather_codes.get(weather_code, "Unknown")
        
        return {
            "city": location["name"],
            "country": location["country"],
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "weather": weather_description,
            "weather_code": weather_code,
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "precipitation": current.get("precipitation"),
            "temperature_unit": temp_unit,
            "timestamp": current.get("time")
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch weather data: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


@mcp.tool()
def get_weather_forecast(city: str, days: int = 7, temperature_unit: str = "celsius") -> Dict[str, Any]:
    """
    Get weather forecast for a specified city (up to 16 days).
    
    Args:
        city: City name (e.g., "London", "New York", "Tokyo")
        days: Number of days for forecast (1-16, default: 7)
        temperature_unit: Temperature unit - "celsius" or "fahrenheit" (default: "celsius")
    
    Returns:
        Weather forecast with daily predictions
    """
    try:
        # Get city coordinates
        location = geocode_city(city)
        if "error" in location:
            return location
        
        if days > 16:
            days = 16
        if days < 1:
            days = 1
        
        # Determine temperature unit parameter
        temp_unit = "fahrenheit" if temperature_unit.lower() == "fahrenheit" else "celsius"
        
        # Get forecast data
        params = {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code", 
                     "precipitation_sum", "wind_speed_10m_max"],
            "temperature_unit": temp_unit,
            "wind_speed_unit": "kmh",
            "timezone": location.get("timezone", "UTC"),
            "forecast_days": days
        }
        
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        daily = data.get("daily", {})
        
        # Weather code mapping (simplified)
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Foggy", 51: "Light drizzle", 53: "Moderate drizzle",
            55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
            81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
            96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        
        forecast_list = []
        times = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        weather_code = daily.get("weather_code", [])
        precipitation = daily.get("precipitation_sum", [])
        wind_speed = daily.get("wind_speed_10m_max", [])
        
        for i in range(len(times)):
            wcode = weather_code[i] if i < len(weather_code) else 0
            forecast_list.append({
                "date": times[i],
                "temperature_max": temp_max[i] if i < len(temp_max) else None,
                "temperature_min": temp_min[i] if i < len(temp_min) else None,
                "weather": weather_codes.get(wcode, "Unknown"),
                "weather_code": wcode,
                "precipitation": precipitation[i] if i < len(precipitation) else 0,
                "wind_speed_max": wind_speed[i] if i < len(wind_speed) else 0
            })
        
        return {
            "city": location["name"],
            "country": location["country"],
            "forecast": forecast_list,
            "temperature_unit": temp_unit,
            "forecast_days": days
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch forecast data: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


if __name__ == "__main__":
    # Run the MCP server with SSE transport
    mcp.run(transport="sse")
