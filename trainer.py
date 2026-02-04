import pandas as pd
import numpy as np
import re
import pickle
import pdfplumber
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

#I added 'syllables' because it correlates better with reading difficulty than just length
def count_syllables(word):
    word = word.lower()
    count = 0
    vowels = "aeiou" 
    if word[0] in vowels:
        count += 1
    for i in range(1, len(word)):
        if word[i] in vowels and word[i - 1] not in vowels:
            count += 1
    if word.endswith("e"):
        count -= 1
    if count == 0:
        count += 1
    return count

#dictionary of features using which difficulty of a word is evaluated
def get_word_features(word):
    word = str(word).lower().strip()
    return {
        'length': len(word),
        'syllables': count_syllables(word),
        'unique_chars': len(set(word)),
        'vowel_ratio': len(re.findall(r'[aeiou]', word)) / max(len(word), 1),
        #Words ending in specific suffixes tend to be harder to remember
        'has_suffix': 1 if any(word.endswith(s) for s in ['tion', 'ing', 'ogy', 'ism']) else 0
        }

#The dataset
#In a real app, one would load 'ratings.csv' or an equivalent train file. 
#Here I'm simulating a small labeled dataset of aorund 30 words with known difficulty (0-10 scale)
#Low = Easy (Dog), High = Hard (Existential)
LABELED_DATA = [
    ("cat", 1.5), ("run", 2.0), ("jump", 2.2), ("house", 2.5), ("apple", 2.8),
    ("school", 3.5), ("friend", 3.8), ("garden", 4.0), ("market", 4.2),
    ("planet", 5.5), ("energy", 5.8), ("system", 6.0), ("theory", 6.5),
    ("biology", 7.0), ("quantum", 8.5), ("philosophy", 8.8), ("hypothesis", 9.0),
    ("existential", 9.5), ("idiosyncratic", 9.8), ("structure", 6.2),
    ("mechanism", 7.5), ("ambiguous", 8.2), ("train", 2.5), ("light", 2.2)
]

def run_pipeline(pdf_path="thesaurus.pdf"):
    print("Loading labeled training data:")
    train_df = pd.DataFrame([get_word_features(w) for w, _ in LABELED_DATA])
    train_y = [score for _, score in LABELED_DATA]

    #Initialize Model
    #Using Random Forest because it handles non-linear relationships better than linear regression
    rf = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    
    print(f"Training model on {len(train_df)} labeled examples")
    rf.fit(train_df, train_y)
    
    #Check accuracy on training set to check if the model has correct logic
    score = rf.score(train_df, train_y)
    print(f"Model Training R^2: {score:.3f}")

    #Searching new words
    print(f"Searching PDF: {pdf_path}")
    new_words = set()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    #Clean regex to find words > 3 chars
                    found = re.findall(r'\b[a-zA-Z]{4,}\b', text)
                    new_words.update([w.lower() for w in found])
    except Exception as e:
        print(f"Error reading PDF (is the path right?): {e}")
        return

    print(f"Found {len(new_words)} unique words to process.")
    
    #Prepare data for prediction
    word_list = list(new_words)
    features_list = [get_word_features(w) for w in word_list]
    pred_df = pd.DataFrame(features_list)
    
    #Predict difficulty
    predictions = rf.predict(pred_df)
    
    #Normalize & export
    #Map the 0-10 predictions to a 0.0 to 1.0 range for the game backend
    min_p, max_p = predictions.min(), predictions.max()
    normalized = (predictions - min_p) / (max_p - min_p)
    
    final_output = []
    for word, score in zip(word_list, normalized):
        final_output.append({
            "word": word,
            "difficulty": round(float(score), 3), #Round to save space
            "raw_score": round(float(score * 10), 2)
        })
    
    #Sort just so we can see the hardest words in the file easily
    final_output.sort(key=lambda x: x['difficulty'])

    with open("game_words.json", "w") as f:
        import json
        json.dump(final_output, f, indent=2)
    
    print(f"Done! Saved {len(final_output)} words to game_words.json")

if __name__ == "__main__":
    run_pipeline()
