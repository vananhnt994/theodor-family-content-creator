import json

with open('output/finale_prompts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data.get('scenes', []):
    sn = s.get('scene_number')
    prompt = s.get('bild_prompt', 'KEIN PROMPT')
    print(f"--- Szene {sn}:")
    print(prompt)
    print()
