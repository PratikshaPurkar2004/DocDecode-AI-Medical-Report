from sklearn.feature_extraction.text import HashingVectorizer


_vectorizer = HashingVectorizer(
    n_features=384,
    alternate_sign=False,
    norm="l2",
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),
)


def embed_texts(texts):
    """
    Convert text into fixed-size vectors.
    """
    vectors = _vectorizer.transform(texts)
    return vectors.toarray().tolist()