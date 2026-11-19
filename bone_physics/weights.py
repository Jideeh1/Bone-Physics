"""Vertex group helpers (one Python pass over the mesh, then numpy)."""

import numpy as np


def sparse_groups(obj):
    """All vertex groups of a mesh object as {name: (indices, weights)}."""
    index_to_name = {g.index: g.name for g in obj.vertex_groups}
    idx = {i: [] for i in index_to_name}
    wts = {i: [] for i in index_to_name}
    for v in obj.data.vertices:
        for g in v.groups:
            lst = idx.get(g.group)
            if lst is not None:
                lst.append(v.index)
                wts[g.group].append(g.weight)
    return {
        index_to_name[i]: (np.array(idx[i], dtype=np.int64), np.array(wts[i], dtype=np.float64))
        for i in index_to_name
    }


def dense(sparse_entry, n):
    out = np.zeros(n)
    if sparse_entry is not None:
        idx, w = sparse_entry
        out[idx] = w
    return out
