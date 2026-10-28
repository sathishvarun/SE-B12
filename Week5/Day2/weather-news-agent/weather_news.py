"""
Week 5 Day 2 - AutoGen Weather News Agent (terminal version)
Run:  python weather_news.py
"""

import asyncio
import os

import requests
from ddgs import DDGS
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

# A headline must contain one of these words in its TITLE to count.
WEATHER_WORDS = [
    "weather", "rain", "rainfall", "shower", "forecast", "imd",
    "monsoon", "cyclone", "storm", "thunder", "heatwave",
    "temperature", "drizzle", "downpour", "flood", "fog",
]


def is_weather_headline(result: dict, city: str) -> bool:
    """True only if the TITLE is about weather and the city is mentioned."""
    title = (result.get("title") or "").lower()
    body = (result.get("body") or "").lower()
    about_weather = any(word in title for word in WEATHER_WORDS)
    mentions_city = city.lower() in title or city.lower() in body
    return about_weather and mentions_city


def live_weather(city: str) -> str:
    """Free, keyless live weather data from wttr.in."""
    try:
        url = f"https://wttr.in/{city}?format=j1"
        data = requests.get(url, timeout=10).json()
        now = data["current_condition"][0]
        today = data["weather"][0]
        rain = max(int(h["chanceofrain"]) for h in today["hourly"])
        return (
            "LIVE WEATHER DATA (wttr.in):\n"
            f"Condition now: {now['weatherDesc'][0]['value']}\n"
            f"Temperature now: {now['temp_C']}°C "
            f"(feels like {now['FeelsLikeC']}°C)\n"
            f"Today: high {today['maxtempC']}°C, "
            f"low {today['mintempC']}°C\n"
            f"Humidity: {now['humidity']}%\n"
            f"Highest chance of rain today: {rain}%"
        )
    except Exception as e:
        return f"LIVE WEATHER DATA: unavailable ({e})"


def weather_headlines(city: str) -> str:
    """Recent weather news headlines for the city from DuckDuckGo."""
    queries = [
        (f'"{city}" weather', "d"),
        (f'"{city}" rain', "w"),
    ]
    for query, timelimit in queries:
        try:
            with DDGS() as ddgs:
                results = ddgs.news(
                    query=query,
                    max_results=15,
                    timelimit=timelimit,
                )
        except Exception:
            continue
        good = [r for r in results if is_weather_headline(r, city)][:3]
        if good:
            lines = ["WEATHER NEWS HEADLINES (DuckDuckGo):"]
            for r in good:
                lines.append(
                    f"- {r.get('title')} "
                    f"({r.get('source')}, {r.get('date', 'n/a')[:10]})\n"
                    f"  {r.get('body')}"
                )
            return "\n".join(lines)
    return "WEATHER NEWS HEADLINES: none found today."


def search_weather_news(city: str) -> str:
    """Get TODAY's weather news and live conditions for one city.

    Use this tool ONLY for weather, rain, heat, storms,
    temperature or weather alerts in a city right now.
    Do NOT use it for general trivia or non-weather questions.

    Args:
        city: Name of the city, e.g. "Chennai".

    Returns:
        Live weather data plus any recent weather news headlines.
    """
    return live_weather(city) + "\n\n" + weather_headlines(city)


SYSTEM_MESSAGE = """
You are a weather news reporter.
When given a city, ALWAYS call the search_weather_news tool first.
The tool returns LIVE WEATHER DATA and sometimes NEWS HEADLINES.
Reply in EXACTLY 3 short lines (max 20 words each).
No bullets, no headings.
Line 1: today's main weather condition in the city.
Line 2: temperature and rain chance.
Line 3: a news highlight if there is one, otherwise a practical tip.
Use only facts from the tool result. Never invent numbers.
Ignore headlines from more than a few days ago.
"""


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set in .env")

    city = input("Which city? ").strip()
    if not city:
        raise SystemExit("Please type a city name.")

    model_client = OpenAIChatCompletionClient(model="gpt-4.1-mini")
    agent = AssistantAgent(
        name="weather_news",
        model_client=model_client,
        tools=[search_weather_news],
        system_message=SYSTEM_MESSAGE,
        reflect_on_tool_use=True,
    )

    task = f"Give me today's weather news for {city}."
    try:
        await Console(agent.run_stream(task=task))
    finally:
        await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())