import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
df = pd.read_csv(r'c:\Users\cencen04_\Downloads\ABSA Hotel Santika\Data Preprocessing\dataset_absa_santika_clean.csv', encoding='utf-8-sig')
batch = df.iloc[3700:3800][['review_id','text_review']]
lines = []
for _, r in batch.iterrows():
    lines.append(f"[{r['review_id']}] {r['text_review']}")
    lines.append("")
with open(r'c:\Users\cencen04_\Downloads\ABSA Hotel Santika\_b.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print("done")
