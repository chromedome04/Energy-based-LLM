import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class OneHot:
    """
    Class to represent a one-hot encoding for a (NLTK-processed) book.
    """
    def __init__(self, book_title: str, sentences: list[list[str]], vocabulary: set[str], 
                 min_sentence_length: int, max_sentence_length: int):
        self.book = book_title
        self.sentences = sentences
        self.vocabulary = vocabulary
        self.M = min_sentence_length
        self.L = max_sentence_length
        self.word2idx = {w: i for i, w in enumerate(vocabulary)}
        self.N = len(sentences)
        self.V = len(vocabulary)

        one_hot = np.zeros((self.N, self.L, self.V), dtype=int)
        for i, sent in enumerate(sentences):
            for j, word in enumerate(sent):
                k = self.word2idx[word]
                one_hot[i,j,k] = 1
            gap_idx = self.word2idx['GAP']
            for j in range(len(sent), self.L):
                one_hot[i,j,gap_idx] = 1

        self.onehot_flat = one_hot.reshape(self.N, self.L*self.V)

    def summarize(self) -> None:
        """
        Print the details of the one-hot encoding. 
        """
        sent_lens_freq = {}
        for sent in self.sentences:
            length = len(sent)
            len_str = str(length)
            if len_str in sent_lens_freq:
                sent_lens_freq[len_str] += 1
            else:
                sent_lens_freq[len_str] = 1
        sorted_dict = sorted(sent_lens_freq.items(), key=lambda item: int(item[0]))
        print(f"Number of sentences (N): {self.N}\n")
        print(f"Length of vocabulary: {self.V}\n")
        print(f"Length of sentences count:\n {sorted_dict}\n")

    def plot(self) -> None:
        """
        Plots the (flattened) one-hot encoding.
        """
        plt.figure(figsize=(8,6))
        plt.spy(self.onehot_flat, aspect='auto', markersize=1, color='navy')
        for i in range(0, self.L*self.V-1, self.V):
            plt.axvline(x=i, color='red', linewidth=0.5)
        plt.xlabel(f"Position Slot L (0-{self.L-1}) x Vocab Index (0-{self.V-1}), LxV=(0-{self.L*self.V-1})")
        plt.ylabel(f"Sentences (0-{self.N-1})")
        plt.title(f"One-Hot Encoding of Sentences from {self.book}")
        plt.legend(['Presence', 'Position Delimiter'], loc='lower right')
        plt.show()

    def partition_by_position(self, position: int) -> np.array:
        """
        Partition the flattened one-hot encoding based on position.
        Must be given a valid position (0-indexed)
        """
        if position not in range(0, self.L):
            raise IndexError(f"Given position is not the sentence length range 0-{self.L-1}")
        i = position
        partition = self.onehot_flat[:, i*self.V:(i+1)*self.V]
        return partition
    
    def position_marginals(self, position: int) -> np.array:
        """
        Return the probabilities of seeing each vocab word at the given position.
        """
        partition = self.partition_by_position(position)
        p = partition.mean(axis=0)
        return p
    
    def position_dimensionality(self, position: int) -> tuple[float]:
        """
        Return the entropy and dimensionality of the given sentence position.
        """
        p = self.position_marginals(position)
        entropy = -np.sum(p * np.log2(p+1e-5))
        dimensionality = 2**entropy
        return (entropy, dimensionality)
    
    def position_plot(self, position: int) -> None:
        """
        Return the probability histogram for vocab words for a given position.
        """
        p = self.position_marginals(position)
        gap_prob = p[-1]
        e_d = self.position_dimensionality(position)
        entropy = e_d[0]
        dim = e_d[1]

        plt.figure(figsize=(8,5))
        plt.stem(p)
        plt.title(f"P(word=k) at position {position}")
        plt.suptitle(f"Entropy: {entropy:.4f}, Dimensionality: {dim:.4f}, P(GAP = {gap_prob:.4f})", fontsize=9)
        plt.show()

    def position_frequent_words(self, position: int, threshold: float) -> pd.DataFrame:
        """
        Return a DataFrame that summarizes the most common words for the given 
        position (with probabilities above the given threshold).
        """
        p = self.position_marginals(position)
        df = pd.DataFrame({
            'Word': self.vocabulary,
            'Probability': p
        })
        df_hi = (df[df['Probability'] >= threshold].sort_values('Probability', ascending=False).reset_index(drop=True))
        return df_hi