import json
from pathlib import Path

FILES = [
    Path('m:/stage sys/ConsiliAI/backend/lab_debug_qwen2.5-coder_7b.json'),
    Path('m:/stage sys/ConsiliAI/backend/endpoint_like_qwen2.5-coder_7b.json'),
]

old = 'self.type_specific_projection = TypeSpecificProjection(hidden_dim, hidden_dim)'
new = "self.type_specific_projection = torch.nn.Linear(hidden_dim, hidden_dim)"

for p in FILES:
    if not p.exists():
        print(f"Missing: {p}")
        continue
    txt = p.read_text(encoding='utf-8')
    if old in txt:
        txt = txt.replace(old, new)
        p.write_text(txt, encoding='utf-8')
        print(f"Patched: {p}")
    else:
        print(f"No change needed: {p}")
