with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Line 310-330:")
for i in range(309, 326):
    print(f"{i+1}: {lines[i].strip()[:90]}")

print("\nLine 458-475:")
for i in range(457, 475):
    print(f"{i+1}: {lines[i].strip()[:90]}")

print("\nLine 624-645:")
for i in range(624, 645):
    print(f"{i+1}: {lines[i].strip()[:90]}")
