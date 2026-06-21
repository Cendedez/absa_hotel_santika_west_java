import csv
import json

aspects = ['Kenyamanan', 'Kebersihan', 'Pelayanan', 'Harga', 'Lokasi', 'Fasilitas', 'Makanan']

# Read expert.csv
expert_data = {}
expert_order = []
with open('expert.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = row['ID_Review'].strip()
        if rid:
            expert_data[rid] = row
            expert_order.append(rid)

# Read claude sonnet 4.6.csv
claude_data = {}
with open('claude sonnet 4.6.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = row['ID_Review'].strip()
        if rid:
            claude_data[rid] = row

# Read Indobert.csv
indobert_data = {}
with open('Indobert.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = row['ID_Review'].strip()
        if rid:
            indobert_data[rid] = row

def get_label(val):
    v = val.strip() if val else ''
    if v == '' or v == '-' or v == 'none':
        return '-'
    return v

# Prepare output for both CSV and Markdown
md_lines = []
csv_rows = []

for i, eid in enumerate(expert_order):
    if eid not in claude_data or eid not in indobert_data:
        continue
    
    expert_row = expert_data[eid]
    claude_row = claude_data[eid]
    indobert_row = indobert_data[eid]
    
    text = expert_row['Text_Review']
    text_md = text.replace('|', '\\|').replace('\n', ' ').replace('\r', '')
    
    # Audit to find the "most matching" aspect
    best_aspect = aspects[0]
    best_score = -1
    
    for asp in aspects:
        expert_lbl = get_label(expert_row.get(asp, ''))
        claude_lbl = get_label(claude_row.get(asp, ''))
        indobert_lbl = get_label(indobert_row.get(f'pred_{asp}', ''))
        
        # Calculate agreement score for this aspect
        score = 0
        valid_labels = [lbl for lbl in [expert_lbl, claude_lbl, indobert_lbl] if lbl != '-']
        
        if len(valid_labels) > 0:
            if expert_lbl == claude_lbl == indobert_lbl and expert_lbl != '-':
                score = 3  # All three match
            elif (expert_lbl == claude_lbl and expert_lbl != '-') or \
                 (expert_lbl == indobert_lbl and expert_lbl != '-') or \
                 (claude_lbl == indobert_lbl and claude_lbl != '-'):
                score = 2  # Two match
            else:
                score = 1  # No match, but at least one has a label
        else:
            score = 0  # No labels at all
            
        if score > best_score:
            best_score = score
            best_aspect = asp
            
    selected_aspect = best_aspect
    
    # Get labels for the selected aspect
    expert_lbl = get_label(expert_row.get(selected_aspect, ''))
    claude_lbl = get_label(claude_row.get(selected_aspect, ''))
    indobert_lbl = get_label(indobert_row.get(f'pred_{selected_aspect}', ''))
    
    csv_rows.append([i+1, text, selected_aspect, indobert_lbl, claude_lbl, expert_lbl])
    md_lines.append(f"| {i+1} | {text_md} | {selected_aspect} | {indobert_lbl} | {claude_lbl} | {expert_lbl} |")

# Write CSV
with open('Lampiran_B_1Aspek_Aligned.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['No.', 'text_review', 'Aspek', 'Label INDOBERT', 'Label Claude Sonnet 4.6', 'Label Validasi narasumber'])
    for row in csv_rows:
        writer.writerow(row)

# Write Markdown
with open('output_table_1Aspek.md', 'w', encoding='utf-8') as f:
    f.write("# Tabel Perbandingan Hasil Labeling (1 Aspek per Review)\n\n")
    f.write("| No. | text_review | Aspek | Label INDOBERT | Label Claude Sonnet 4.6 | Label Validasi narasumber |\n")
    f.write("|-----|-------------|-------|----------------|-------------------------|---------------------------|\n")
    for line in md_lines:
        f.write(line + "\n")

print("Files generated: Lampiran_B_1Aspek.csv and output_table_1Aspek.md")
