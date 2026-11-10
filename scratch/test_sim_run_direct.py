import sys, os
sys.path.insert(0, os.getcwd())
from services.simulation_engine import SimulationEngine
import logging

logging.basicConfig(level=logging.INFO)
print("Running simulation for 2026-11-05...")
sim = SimulationEngine(owner="local:nebioglur")
sim.run_daily_simulation("2026-11-05")
print("Finished run_daily_simulation.")
