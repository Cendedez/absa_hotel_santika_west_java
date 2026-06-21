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
    if v == '' or v == '-':
        return '-'
    if v == 'none':
        return '-'
    return v

# Generate markdown table
lines = []

for i, eid in enumerate(expert_order):
    if eid not in claude_data or eid not in indobert_data:
        continue
    
    expert_row = expert_data[eid]
    claude_row = claude_data[eid]
    indobert_row = indobert_data[eid]
    
    text = expert_row['Text_Review'].replace('|', '\\|').replace('\n', ' ').replace('\r', '')
    
    # Get labels per aspect
    indobert_labels = []
    claude_labels = []
    expert_labels = []
    
    for asp in aspects:
        # IndoBERT: use pred_ columns (actual predictions)
        pred_key = f'pred_{asp}'
        ib_val = get_label(indobert_row.get(pred_key, ''))
        indobert_labels.append(f"{asp}: {ib_val}")
        
        # Claude
        cl_val = get_label(claude_row.get(asp, ''))
        claude_labels.append(f"{asp}: {cl_val}")
        
        # Expert
        ex_val = get_label(expert_row.get(asp, ''))
        expert_labels.append(f"{asp}: {ex_val}")
    
    indobert_str = ', '.join(indobert_labels)
    claude_str = ', '.join(claude_labels)
    expert_str = ', '.join(expert_labels)
    
    lines.append(f"| {i+1} | {text} | {indobert_str} | {claude_str} | {expert_str} |")

# Write the output
with open('output_table.md', 'w', encoding='utf-8') as f:
    f.write("# Tabel Perbandingan Hasil Labeling ABSA Hotel Santika\n\n")
    f.write("Tabel ini membandingkan 150 data review yang dilabel oleh **Expert (Narasumber Profesional)** dengan hasil labeling dari **IndoBERT** dan **Claude Sonnet 4.6**.\n\n")
    f.write("**Keterangan Label:**\n")
    f.write("- `positif` = Sentimen positif\n")
    f.write("- `negatif` = Sentimen negatif\n") 
    f.write("- `netral` = Sentimen netral\n")
    f.write("- `-` = Aspek tidak terdeteksi/tidak relevan\n\n")
    f.write("**Aspek yang dianalisis:** Kenyamanan, Kebersihan, Pelayanan, Harga, Lokasi, Fasilitas, Makanan\n\n")
    f.write("| No. | Text Review | Label IndoBERT | Label Claude Sonnet 4.6 | Label Validasi Narasumber |\n")
    f.write("|-----|-------------|----------------|-------------------------|---------------------------|\n")
    for line in lines:
        f.write(line + "\n")

print(f"Generated table with {len(lines)} rows")
print("Written to output_table.md")
