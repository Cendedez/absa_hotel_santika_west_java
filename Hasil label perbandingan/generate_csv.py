import csv

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

# Generate CSV output
with open('Lampiran_B_Perbandingan_Labeling.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    
    # Header
    header = ['No.', 'ID_Review', 'Text_Review']
    for asp in aspects:
        header.append(f'IndoBERT_{asp}')
    for asp in aspects:
        header.append(f'Claude_{asp}')
    for asp in aspects:
        header.append(f'Expert_{asp}')
    writer.writerow(header)
    
    # Data rows
    for i, eid in enumerate(expert_order):
        if eid not in claude_data or eid not in indobert_data:
            continue
        
        expert_row = expert_data[eid]
        claude_row = claude_data[eid]
        indobert_row = indobert_data[eid]
        
        text = expert_row['Text_Review']
        
        row_data = [i+1, eid, text]
        
        # IndoBERT predictions
        for asp in aspects:
            pred_key = f'pred_{asp}'
            row_data.append(get_label(indobert_row.get(pred_key, '')))
        
        # Claude labels
        for asp in aspects:
            row_data.append(get_label(claude_row.get(asp, '')))
        
        # Expert labels
        for asp in aspects:
            row_data.append(get_label(expert_row.get(asp, '')))
        
        writer.writerow(row_data)

print("CSV saved: Lampiran_B_Perbandingan_Labeling.csv")
