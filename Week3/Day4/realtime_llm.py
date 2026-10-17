import json
import requests
from openai import OpenAI

client = OpenAI(api_key="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")

def fetch_realtime_weather(city: str):
    """Fetch live coordinates and current weather."""
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    geo_res = requests.get(geo_url).json()
    
    if not geo_res.get("results"):
        return None

    location = geo_res["results"][0]
    lat, lon = location["latitude"], location["longitude"]
    resolved_name = location.get("name", city)

    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    weather_res = requests.get(weather_url).json()
    
    return resolved_name, weather_res.get("current_weather")

def analyze_weather_data(city: str, live_data: dict):
    """Pass live data into the LLM with guaranteed JSON output."""
    prompt = f"""
    Live real-time weather feed:
    - City: {city}
    - Temperature: {live_data.get('temperature')}°C
    - Wind Speed: {live_data.get('windspeed')} km/h
    - Weather Code: {live_data.get('weathercode')}

    Return a valid JSON object matching this schema:
    {{
      "summary": "Concise 1-sentence weather overview",
      "alert_level": "None" | "Advisory" | "Severe",
      "outdoor_recommendation": "Short tip for outdoor activities",
      "clothing_advice": "What to wear"
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an automated meteorological analyzer that outputs only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)

if __name__ == "__main__":
    while True:
        target_city = input("\nEnter city name (or type 'exit' to quit): ").strip()
        if target_city.lower() in ("exit", "quit"):
            break
        if not target_city:
            continue

        result = fetch_realtime_weather(target_city)
        if not result or not result[1]:
            print(f"City '{target_city}' not found.")
            continue

        city_name, live_data = result
        print(f"\n[Raw Telemetry] {city_name}: {live_data['temperature']}°C, Wind {live_data['windspeed']} km/h")
        
        parsed_ai_response = analyze_weather_data(city_name, live_data)
        print("\n[AI Structured Analysis]")
        print(json.dumps(parsed_ai_response, indent=2))