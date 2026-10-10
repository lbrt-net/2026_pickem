"""Automated checks for the rules that matter (see ROADMAP "Engineering foundation").

tests/*.py run without a database: they test the pure rules — scoring, Rec bid, roster fit, waivers' "real move" logic,
the round robin, auction budgets. The app reads its config from the environment at import, so fill in harmless values.
"""
import os

# Full-flow checks (tests/integration) need a throwaway Postgres: TEST_DATABASE_URL. The app connects to DATABASE_URL.
if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

for k, v in {"DISCORD_CLIENT_ID": "x", "DISCORD_CLIENT_SECRET": "x", "DISCORD_REDIRECT_URI": "x", "SECRET_KEY": "x",
             "DATABASE_URL": "postgresql://test/none", "ADMIN_DISCORD_IDS": "", "INTERNAL_API_KEY": "test"}.items():
    os.environ.setdefault(k, v)
