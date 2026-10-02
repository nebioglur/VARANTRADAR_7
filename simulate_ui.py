from services.antigravity_core import AntigravityCore
from services.scoring import ScoringEngine

def simulate_update():
    print("Initializing Core...")
    core = AntigravityCore()
    core.initialize_system()
    
    print("Updating all data (simulating 'Verileri Güncelle' button)...")
    core.update_all_data()
    
    print("Calculating indicators for ASELS.IS (1d)...")
    df = core.analyzer.calculate_indicators("ASELS.IS", "1d")
    
    print(f"Dataframe size: {len(df)}")
    if not df.empty:
        print(f"Latest Close Price: {df['close'].iloc[-1]}")
    
    scorer = ScoringEngine()
    score = scorer.generate_score("ASELS.IS", "1d")
    print(f"Score Data: {score}")

if __name__ == "__main__":
    simulate_update()
