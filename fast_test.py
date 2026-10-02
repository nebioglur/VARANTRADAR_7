import sys
import json
from services.tavan_tracker import TavanAuditTracker
res = TavanAuditTracker.get_long_term_history()
print("LEN DAILY:", len(res.get("daily_breakdown", [])))
