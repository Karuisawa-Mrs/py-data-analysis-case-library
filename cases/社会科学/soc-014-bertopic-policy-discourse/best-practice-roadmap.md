# Best-Practice Roadmap: soc-014-bertopic-policy-discourse

## Current Implementation (Fallback)
Due to Windows compilation issues with `bertopic` and `sentence-transformers`, the current `analysis.py` uses:
- **sklearn LDA** (Latent Dirichlet Allocation) as the topic model
- **sklearn TfidfVectorizer** for text representation
- **pyLDAvis-style topic-term outputs** exported as CSV

## Target Best-Practice Implementation
Once dependencies are installable, migrate to:

### 1. BERTopic (Neural Topic Modeling)
**Library**: `MaartenGr/BERTopic` (https://github.com/MaartenGr/BERTopic)
**Installation**: `pip install bertopic`
**Code pattern**:
```python
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

# Embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# BERTopic pipeline
topic_model = BERTopic(
    embedding_model=embedding_model,
    umap_model=umap.UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine'),
    hdbscan_model=hdbscan.HDBSCAN(min_cluster_size=15, metric='euclidean', cluster_selection_method='eom'),
    vectorizer_model=CountVectorizer(stop_words='english'),
    nr_topics='auto',  # Optional: merge similar topics
    verbose=True,
)

topics, probs = topic_model.fit_transform(docs)

# Outputs
 topic_info = topic_model.get_topic_info()
 topic_terms = {t: topic_model.get_topic(t) for t in topic_info.Topic if t != -1}
 topic_distr = topic_model.approximate_distribution(docs)

# Visualization (optional)
 topic_model.visualize_topics()
 topic_model.visualize_barchart()
 topic_model.visualize_heatmap()
```
**Artifacts to add**:
- `outputs/topic_embeddings_2d.csv` — UMAP-projected document embeddings
- `outputs/topic_hierarchy.json` — Hierarchical topic merging tree
- `outputs/intertopic_distance_map.html` — pyLDAvis-style interactive map

### 2. Dynamic Topic Modeling (optional extension)
**Code pattern**:
```python
# If documents have timestamps
topics_over_time = topic_model.topics_over_time(docs, timestamps=timestamps)
topic_model.visualize_topics_over_time(topics_over_time)
```

### 3. Migration Steps
1. Install `bertopic` and `sentence-transformers`
   - Windows note: these are pure Python + torch; should work if torch is installed
   - `pip install bertopic sentence-transformers`
2. In `analysis.py`, detect availability:
   ```python
   try:
       from bertopic import BERTopic
       from sentence_transformers import SentenceTransformer
       HAS_BERTOPIC = True
   except ImportError:
       HAS_BERTOPIC = False
   ```
3. Replace LDA branch with BERTopic pipeline
4. Keep LDA as fallback when BERTopic absent
5. Update `expected_artifacts` in `index.md`
6. Update `method_tags` to include `BERTopic`, `Sentence Transformers`, `UMAP`, `HDBSCAN`

### 4. Validation After Migration
```bash
python analysis.py --smoke-test
# Should produce: topic_info.csv, topic_document_map.csv, topic_terms.csv,
# topic_prevalence.png, AND topic_embeddings_2d.csv
```
