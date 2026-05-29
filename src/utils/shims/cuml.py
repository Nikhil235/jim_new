import numpy as np

class hidden_markov_model:
    class GaussianHMM:
        def __init__(self, n_components=3, max_iter=100, covariance_type="diag", random_state=42):
            from src.utils.gpu_models import CuPyGaussianHMM
            self.model = CuPyGaussianHMM(n_components, max_iter, covariance_type, random_state)
            
        def fit(self, X):
            return self.model.fit(X)
            
        def predict(self, X):
            return self.model.predict(X)
            
        def score(self, X):
            return self.model.score(X)

# Map common imports
GaussianHMM = hidden_markov_model.GaussianHMM
