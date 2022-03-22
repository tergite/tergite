from itertools import groupby

from typing import List, Tuple, Union, Any, Dict

def iqx_rle(
    seq : List[Any]
) -> List[ Union[ Tuple[Any], Tuple[Any, int] ] ]:
    """
    Run-length encodes a sequence.
    Constant subsequences are stored as a single term and count, rather than as the original subsequence.
    Counts equal to 1 are omitted.
    """
    seq = [ ( k, sum(1 for _ in g) ) for k, g in groupby(seq) ]
    return [ (c,rep) if rep > 1 else (c,) for c,rep in seq ]

def iqx_rld(
    enc_seq : List[ Union[ Tuple[Any], Tuple[Any, int] ] ]
) -> List[Any] :
    """
    Decodes a run-length encoded sequence. Omitted counts are interpreted as 1.
    """
    dec = [ [ t[0] for _ in range(t[1]) ] if len(t) == 2 else [ t[0] ] for t in enc_seq ]
    return [item for sublist in dec for item in sublist]