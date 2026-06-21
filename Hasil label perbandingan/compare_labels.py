import csv
import json

# Read expert.csv
expert_data = {}
with open('expert.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = row['ID_Review'].strip()
        if rid:
            expert_data[rid] = row

# Read claude sonnet 4.6.csv
claude_data = {}
with open('claude sonnet 4.6.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = row['ID_Review'].strip()
        if rid:
            claude_data[rid] = row

# Read Indobert.csv - note different column names for labels
indobert_data = {}
with open('Indobert.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = row['ID_Review'].strip()
        if rid:
            indobert_data[rid] = row

# Get expert IDs (in order)
expert_ids = list(expert_data.keys())

print(f"Total expert reviews: {len(expert_ids)}")
print(f"Total claude reviews: {len(claude_data)}")
print(f"Total indobert reviews: {len(indobert_data)}")

# Check which expert IDs exist in both claude and indobert
matching_ids = []
missing_claude = []
missing_indobert = []

for eid in expert_ids:
    in_claude = eid in claude_data
    in_indobert = eid in indobert_data
    if in_claude and in_indobert:
        matching_ids.append(eid)
    if not in_claude:
        missing_claude.append(eid)
    if not in_indobert:
        missing_indobert.append(eid)

print(f"\nMatching IDs (in all 3): {len(matching_ids)}")
print(f"Missing from claude: {len(missing_claude)} -> {missing_claude}")
print(f"Missing from indobert: {len(missing_indobert)} -> {missing_indobert}")

# Aspect categories
aspects = ['Kenyamanan', 'Kebersihan', 'Pelayanan', 'Harga', 'Lokasi', 'Fasilitas', 'Makanan']

# Build output data
results = []
for i, eid in enumerate(matching_ids):
    expert_row = expert_data[eid]
    claude_row = claude_data[eid]
    indobert_row = indobert_data[eid]
    
    text = expert_row['Text_Review']
    
    # Expert labels per aspect
    expert_labels = {}
    for asp in aspects:
        val = expert_row.get(asp, '').strip()
        expert_labels[asp] = val if val else '-'
    
    # Claude labels per aspect
    claude_labels = {}
    for asp in aspects:
        val = claude_row.get(asp, '').strip()
        claude_labels[asp] = val if val else '-'
    
    # IndoBERT labels per aspect - column names have "label_" prefix AND "pred_" prefix
    # The "label_" columns seem to be the same as claude (ground truth from model)
    # The "pred_" columns are the actual IndoBERT predictions
    indobert_labels = {}
    for asp in aspects:
        # Try pred_ columns first (actual predictions)
        pred_key = f'pred_{asp}'
        label_key = f'label_{asp}'
        val = indobert_row.get(pred_key, '').strip()
        if not val:
            val = indobert_row.get(label_key, '').strip()
        indobert_labels[asp] = val if val else '-'
    
    # Also get the label_ version for comparison
    indobert_label_labels = {}
    for asp in aspects:
        label_key = f'label_{asp}'
        val = indobert_row.get(label_key, '').strip()
        indobert_label_labels[asp] = val if val else '-'
    
    results.append({
        'no': i + 1,
        'id': eid,
        'text': text,
        'indobert_labels': indobert_labels,
        'indobert_label_labels': indobert_label_labels,
        'claude_labels': claude_labels,
        'expert_labels': expert_labels,
    })

# Print first few rows to verify
for r in results[:3]:
    print(f"\n--- Review #{r['no']} (ID: {r['id']}) ---")
    print(f"Text: {r['text'][:80]}...")
    print(f"IndoBERT pred: {r['indobert_labels']}")
    print(f"IndoBERT label: {r['indobert_label_labels']}")
    print(f"Claude: {r['claude_labels']}")
    print(f"Expert: {r['expert_labels']}")

# Save as JSON for artifact creation
with open('comparison_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(results)} results to comparison_results.json")
