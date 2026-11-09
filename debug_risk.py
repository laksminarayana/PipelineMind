import sys
from pathlib import Path
ROOT_DIR = Path("G:/pipeline")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

print("Line 1: Policy set", flush=True)
from backend.app.analyzers.risk_analyzer import risk_analyzer
print("Line 2: Imported risk_analyzer", flush=True)

async def debug():
    print("Point 1: starting async function", flush=True)
    res = await risk_analyzer.analyze(db_config_diff="+DB_HOST=test", strategy="rolling")
    print(f"Point 2: analyze finished, score={res['risk_score']}", flush=True)

asyncio.run(debug())
print("Line 3: All complete!", flush=True)
