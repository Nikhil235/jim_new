import pandas as pd
import cupy as cp

def from_pandas(df):
    """Shim for cuDF.from_pandas"""
    return df

class Series(pd.Series):
    """Shim for cuDF.Series"""
    pass

class DataFrame(pd.DataFrame):
    """Shim for cuDF.DataFrame"""
    pass

class Index(pd.Index):
    """Shim for cuDF.Index"""
    pass

class DatetimeIndex(pd.DatetimeIndex):
    """Shim for cuDF.DatetimeIndex"""
    pass

class MultiIndex(pd.MultiIndex):
    """Shim for cuDF.MultiIndex"""
    pass



def Series_rolling_std(self, window):
    """GPU-accelerated rolling std for the shim"""
    return self.rolling(window).std()
