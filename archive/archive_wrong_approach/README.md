# Archive Note - Wrong Approach Files

## Files in this folder use WRONG train/test split approach

These files were moved here because they use traditional ML train/test split, which is NOT how Pine Script works:

- `fetch_split_data.py` - Creates separate training/testing datasets
- `test_with_split_data.py` - Uses train/test split approach

## Why this is wrong:

Pine Script uses continuous learning on ALL available data. There is no concept of separate training and testing sets. The ML model learns and predicts simultaneously as new bars arrive.

## Correct approach:

Use the files in the main directory:
- `fetch_pinescript_style_data.py` - Single dataset, no split
- `test_pinescript_style.py` - Continuous learning implementation

## Key difference:

```python
# ❌ WRONG (Traditional ML)
train_data = data[:1700]
test_data = data[1700:]

# ✅ CORRECT (Pine Script)
for bar in all_data:
    ml.update_and_predict(bar)
```

---

**These files are kept for reference but should NOT be used for Pine Script replication.**
