import pandas as pd
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re

INPUT_CSV = 'finance_actions_for_ai.csv'
OUTPUT_CSV = 'finance_actions_textrank.csv'

# Load data
df = pd.read_csv(INPUT_CSV)

# Only consider actionable (not completed) rows
mask = ~df['status'].str.lower().eq('completed')
df_actionable = df[mask].copy()

# Combine name and notes for text analysis
def clean_text(x):
    if pd.isnull(x):
        return ''
    return re.sub(r'[^\w\s]', '', str(x)).lower()

def has_keywords(text, keywords):
    return any(kw in text for kw in keywords)

texts = (df_actionable['name'].fillna('') + ' ' + df_actionable['notes'].fillna('')).apply(clean_text).tolist()

# TF-IDF vectorization
vectorizer = TfidfVectorizer(stop_words='english')
X = vectorizer.fit_transform(texts)

# Cosine similarity matrix
sim_matrix = cosine_similarity(X)

# Build similarity graph
G = nx.from_numpy_array(sim_matrix)

# Run TextRank (PageRank on similarity graph)
pagerank = nx.pagerank(G, max_iter=1000)

# Assign scores back to dataframe
df_actionable['TextRank_Score'] = df_actionable.index.map(lambda i: pagerank.get(i, 0))
# Add original TextRank rank (1=highest)
df_actionable['TextRank_Rank'] = df_actionable['TextRank_Score'].rank(ascending=False, method='min').astype(int)

# Hybrid adjustment
scenario_words = [
    'scenario', 'what if', 'someday', 'maybe', 'reference', 'plan', 'wish', 'dream', 'explore', 'consider',
    'could', 'would', 'want', 'future', 'eventually', 'long term', 'goal', 'aspiration', 'communication', 'consolidate essential info'
]
high_impact_words = [
    'living will', 'life insurance', 'update will', 'beneficiary', 'power of attorney', 'close account', 'consolidate accounts',
    'tax', 'urgent', 'deadline', 'required', 'must', 'critical', 'important'
]
annual_words = [
    'annual', 'recurring', 'dues', 'monthly', 'allowance', 'cell phone bill', 'review'
]
demote_words = ['wedding', 'google storage']

suggested_projects = []
hybrid_scores = []
for i, row in df_actionable.iterrows():
    text = clean_text(row['name']) + ' ' + clean_text(row['notes'])
    score = pagerank.get(i, 0)
    # Project assignment
    if has_keywords(text, annual_words):
        suggested_projects.append('Annual/Recurring Tasks')
    elif has_keywords(text, scenario_words):
        suggested_projects.append('Reference/Incubate')
    else:
        suggested_projects.append('Actionable')
    # Demote
    if has_keywords(text, scenario_words) or has_keywords(text, demote_words):
        score = 0  # Lowest
    # Promote
    if has_keywords(text, high_impact_words):
        score = 1e6  # Highest
    hybrid_scores.append(score)

df_actionable['HybridRank_Score'] = hybrid_scores
df_actionable['HybridRank_Rank'] = pd.Series(hybrid_scores).rank(ascending=False, method='min').astype(int).values
df_actionable['Suggested_Project'] = suggested_projects
df_actionable['ManualOverride'] = ''

# Merge back into original df
for col in ['TextRank_Score', 'TextRank_Rank', 'HybridRank_Score', 'HybridRank_Rank', 'Suggested_Project', 'ManualOverride']:
    df[col] = None
    df.loc[mask, col] = df_actionable[col]

# Save to new CSV
df.to_csv(OUTPUT_CSV, index=False)

# Print top 10 actionable actions by HybridRank
print('Top 10 actionable actions by HybridRank:')
top10 = df_actionable[(df_actionable['Suggested_Project'] == 'Actionable')].sort_values('HybridRank_Score', ascending=False).head(10)
for i, row in top10.iterrows():
    print(f"{row['HybridRank_Rank']}. {row['name']} (Score: {row['HybridRank_Score']})") 