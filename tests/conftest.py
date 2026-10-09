"""Automated checks for the rules that matter (see ROADMAP "Engineering foundation").

These run without a database: they test the pure rules — scoring, Rec bid, roster fit, waivers' "real move" logic,
the round robin, auction budgets. The app reads its config from the environment at import, so fill in harmless values.
"""
import os

for k, v in {"DISCORD_CLIENT_ID": "x", "DISCORD_CLIENT_SECRET": "x", "DISCORD_REDIRECT_URI": "x", "SECRET_KEY": "x",
             "DATABASE_URL": "postgresql://test/none", "ADMIN_DISCORD_IDS": "", "INTERNAL_API_KEY": "test"}.items():
    os.environ.setdefault(k, v)
