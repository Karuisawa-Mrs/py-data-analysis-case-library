# Best-Practice Roadmap: soc-017-public-feedback-sentiment-modeling

## Current Implementation (Fallback)
Due to Windows compilation issues with `transformers` (actually transformers should work since torch is installed... but let's be safe), the current `analysis.py` uses:
- **sklearn TfidfVectorizer** with n-grams (1-3) and char-level features
- **Logistic Regression** classifier
- **Cross-validated grid search** for hyperparameters

## Target Best-Practice Implementation
Once fully validated, migrate to:

### 1. Transformer-based Text Classification
**Library**: `huggingface/transformers` (https://github.com/huggingface/transformers)
**Installation**: `pip install transformers`
**Code pattern**:
```python
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    Trainer, TrainingArguments,
)
from datasets import Dataset

# Load pre-trained model and tokenizer
model_name = "distilbert-base-uncased-finetuned-sst-2-english"
# For Chinese: "bert-base-chinese" or "distilbert-base-chinese"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

# Prepare dataset
def tokenize_function(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True)

dataset = Dataset.from_pandas(df)
tokenized = dataset.map(tokenize_function, batched=True)

# Fine-tune (or just inference if already fine-tuned)
training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["test"],
)
trainer.train()

# Predictions
predictions = trainer.predict(tokenized["test"])
```
**Artifacts to add**:
- `outputs/transformer_metrics.csv` — Accuracy, F1, precision, recall from transformer
- `outputs/confidence_distribution.png` — Distribution of softmax probabilities
- `outputs/misclassified_examples.csv` — Top-K misclassified samples for error analysis

### 2. Attention-based Interpretability
**Code pattern**:
```python
from transformers import AutoTokenizer, AutoModel
import torch

# Extract attention weights
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name, output_attentions=True)

inputs = tokenizer(text, return_tensors="pt", truncation=True)
outputs = model(**inputs)
attentions = outputs.attentions  # Tuple of (layers, batch, heads, seq_len, seq_len)

# Aggregate and visualize attention for [CLS] token
cls_attention = attentions[-1][0, :, 0, :].mean(dim=0).detach().numpy()
```
**Artifacts to add**:
- `outputs/attention_heatmap.png` — Attention weights for sample texts

### 3. Migration Steps
1. Install `transformers` and `datasets`
   - `pip install transformers datasets`
   - Windows note: depends on `torch`; ensure torch is already installed
2. In `analysis.py`, detect availability:
   ```python
   try:
       from transformers import AutoTokenizer, AutoModelForSequenceClassification
       HAS_TRANSFORMERS = True
   except ImportError:
       HAS_TRANSFORMERS = False
   ```
3. Add transformer branch alongside TF-IDF baseline
4. Keep TF-IDF as interpretable baseline; transformer as advanced model
5. Update `expected_artifacts` in `index.md`
6. Update `method_tags` to include `BERT`, `Transformers`, `Fine-tuning`

### 4. Note on Current Fallback
The current TF-IDF + Logistic Regression fallback is intentionally enhanced with:
- N-gram range (1,3) for phrase capture
- Character-level n-grams for robustness to misspellings
- Class-weight balancing for imbalanced sentiment
- Cross-validated hyperparameter search

These enhancements make the fallback reasonably strong while staying fully within sklearn.

### 5. Validation After Migration
```bash
python analysis.py --smoke-test
# Should produce: model_metrics.csv, classification_report.csv,
# confusion_matrix.png, top_terms_or_attention.csv,
# AND transformer_metrics.csv, confidence_distribution.png
```
