# 🎧 AI Customer Support Desk — AutoGen + Streamlit

Weekly Buildathon (Social Eagle · Gen AI Architect Program). Three AutoGen agents run in sequence with `RoundRobinGroupChat`:

| # | Agent | Tool | Job |
|---|---|---|---|
| 1 | Assistant | – | Answers from its own knowledge |
| 2 | Web_Search_Assistant | `web_search` (Serper) | Searches the web, answers from results with sources |
| 3 | Entry_Agent | `save_to_file` | Saves query + both answers to `answers.txt`, says TERMINATE |

**Extras:** live agent progress (`run_stream`), model / tone / temperature settings, customer name, category & priority, ticket IDs, sample questions, clickable web sources, 👍/👎 feedback, transcript download, ticket history with search & stats.

## Run (macOS)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then add your keys in .env
streamlit run app.py
```
Open http://localhost:8501

Keys are read from environment variables / `.env` and are never committed.
