import pandas as pd
import re
import nltk
from nltk import pos_tag
from nltk.corpus import gutenberg
from nltk.tokenize import sent_tokenize, RegexpTokenizer
from IPython.display import display

nltk.download('gutenberg')
tokenizer = RegexpTokenizer(r'\w+')

PUNCT = set("`!@#$%^&*()_-+=[]|;:<>,.?/{\}")

def list_available_books() -> dict[str, str]:
    """
    Returns a dictionary with titles and corresponding filenames for all the 
    available books we can use in the NLTK gutenberg corpus. Also displays
    a DataFrame summarizing this information so it's easy to copy to the 
    filename for input into the Book class.
    """
    books = gutenberg.fileids()
    title_file = {}
    for b in books:
        title_s = gutenberg.sents(b)[0]
        del title_s[0]
        del title_s[-1]
        if "'" in title_s:
            i = title_s.index("'")
            posses = []
            first = title_s[i-1]
            posses.append(first)
            apost = title_s[i]
            posses.append(apost)
            last = title_s[i+1]
            posses.append(last)
            single = "".join(posses)
            title_s.insert(i-1, single)
            for k in range(i, i+3):
                title_s.pop(i)
        if 'by' in title_s:
            s = title_s.index('by')
            title = " ".join(title_s[:s])
            if title not in title_file:
                title_file[title] = b
        else:
            title = " ".join(title_s)
            if title not in title_file:
                title_file[title] = b

    titles = title_file.keys()
    filenames = title_file.values()
    books_df = pd.DataFrame({
        'Title': titles,
        'Filename': filenames
    })
    display(books_df)
    return title_file

def is_roman(word):
    """
    Checks if the given word is a roman numeral.
    """
    pattern = re.compile(r"""
    ^M{0,3}
    (CM|CD|D?C{0,3})?
    (XC|XL|L?X{0,3})?
    (IX|IV|V?I{0,3})?
    $
    """, re.VERBOSE | re.IGNORECASE)
    return bool(re.match(pattern, word))

def get_sents(filename: str, is_gutenberg: bool = True) -> list[list[str]]:
    """
    Given a filename for a NLTK gutenberg corpus text (provided by the 
    list_available_books function), return a list of sentences, where each
    sentence is comprised of each word (string). If gutenberg is False, 
    assumes the file is a plain text file with one sentence per line.
    """
    if is_gutenberg:
        return gutenberg.sents(filename)
    else:
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()
        sentences = sent_tokenize(text)
        return [tokenizer.tokenize(sent) for sent in sentences]
    
def merged_books_sents(filenames: list[tuple[str, bool]]) -> list[list[str]]:
    """
    Given a list of filenames and boolean indicators for whether they are 
    available in the nltk.gutenberg corpus, return a merged list of sentences
    for all sentences across all passed books.
    """
    all = []
    for b in filenames:
        all.extend(get_sents(b[0], b[1]))
    return all

def clean_sents(sentences: str, min_sent_len: int, 
               max_sent_len: int) -> list[list[str]]:
    """
    Given a filename for a NLTK gutenberg corpus text (provided by the 
    list_available_books function), return a cleaned list of sentences, where
    each sentence is comprised of each word (string). Removes chapter titles, 
    punctuation, and other unwanted characters.
    """
    filtered = [s for s in sentences if min_sent_len <= len(s) <= max_sent_len+1]
    cleaned = []
    for sent in filtered:
        if any(tok == "CHAPTER" for tok in sent):
            continue
        lowered = [tok.lower() for tok in sent]
        if "chapter" in lowered:
            i = lowered.index("chapter")
            if i + 1 < len(sent):
                nxt = sent[i + 1]
                if nxt.isdigit() or is_roman(nxt):
                    continue
        sent = pos_tag(sent)
        clean = []
        for word, PoS in sent:
            if not re.search(r"[A-Za-z0-9]", word):
                continue
            if word.isdigit():
                continue
            if len(word) > 1 and is_roman(word):
                continue
            if word in PUNCT:
                continue
            if PoS == 'NNP':
                clean.append(word)
                continue
            w = word.strip("_" + "".join(PUNCT)).lower()
            if not w:
                continue
            if len(w) == 1 and w not in ('a', 'i'):
                continue
            clean.append(w)
        if min_sent_len <= len(clean) <= max_sent_len:
            cleaned.append(clean)

    return cleaned

def get_vocabulary(cleaned_book: list[list[str]]) -> set[str]:
    """
    Given a clean book, returns a set of the unique vocabulary words that appear
    in the book.
    """
    vocab = set()
    for sent in cleaned_book:
        for w in sent:
            vocab.add(w)
    vocab.add('GAP')
    return sorted(vocab)
