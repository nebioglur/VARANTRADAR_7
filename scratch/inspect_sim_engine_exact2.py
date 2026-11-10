with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Line 840-870:")
for i in range(839, 870):
    print(f"{i+1}: {lines[i].strip()[:90]}")

print("\nLine 910-955:")
for i in range(909, 955):
    print(f"{i+1}: {lines[i].strip()[:90]}")
