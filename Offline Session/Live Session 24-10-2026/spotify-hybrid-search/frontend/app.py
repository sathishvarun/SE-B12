import os
import requests
import streamlit as st

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8002",
)

st.set_page_config(
    page_title="Spotify Hybrid Search",
    page_icon="🎵",
    layout="wide",
)

st.title("🎵 Spotify Hybrid Search")
st.write("Search music using keywords and semantic similarity.")

query = st.text_input(
    "What would you like to listen to?",
    placeholder="e.g. music for sleeping",
)

search_type = st.selectbox(
    "Search method",
    ["Hybrid Search", "Semantic Search", "Keyword Search"],
)

if st.button("Search", type="primary"):
    if not query.strip():
        st.warning("Please enter a search query.")
    else:
        endpoints = {
            "Hybrid Search": "/hybrid-search",
            "Semantic Search": "/semantic-search",
            "Keyword Search": "/search",
        }

        try:
            response = requests.get(
                API_URL + endpoints[search_type],
                params={"query": query.strip(), "type": "all"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])

            if not results:
                st.info("No matching music found.")
            else:
                st.success(f"Found {len(results)} results.")

                for item in results:
                    with st.container(border=True):
                        st.subheader(item.get("title", "Untitled"))
                        st.write(
                            f"**Artist:** {item.get('artist', 'Unknown')}"
                        )
                        st.write(
                            f"**Type:** {item.get('type', 'Unknown')}"
                        )

                        if item.get("album"):
                            st.write(f"**Album:** {item['album']}")

                        if item.get("genre"):
                            st.write(f"**Genre:** {item['genre']}")

                        if item.get("description"):
                            st.write(item["description"])

                        if item.get("hybrid_score") is not None:
                            st.caption(
                                f"Hybrid score: {item['hybrid_score']}"
                            )
                        elif item.get("score") is not None:
                            st.caption(
                                f"Similarity score: {item['score']}"
                            )

        except requests.RequestException as exc:
            st.error(f"Could not connect to the API: {exc}")
