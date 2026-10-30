"""Disjoint Set Union (Union-Find) with union by rank and path compression.

Used by Kruskal to reject cycle-forming roads and by the pipeline to answer
"are these two sites in the same connected component?" in near O(1).

Invariant: parent[x] == x  <=>  x is the representative (root) of its set.
Every set is a tree of parent pointers; rank[r] is an upper bound on the
height of the tree rooted at r.
"""


class DSU:
    def __init__(self, items):
        # MAKE-SET for every item: each item starts alone, as its own root.
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}

    def find(self, x):
        """Return the root of x's set, compressing the path on the way back."""
        root = x
        while self.parent[root] != root:          # walk up to the root
            root = self.parent[root]
        while self.parent[x] != root:             # path compression:
            nxt = self.parent[x]                  # point every node on the
            self.parent[x] = root                 # path directly at the root
            x = nxt
        return root

    def union(self, a, b):
        """Merge the sets of a and b. Return False if they were already one set
        (for Kruskal this means the road would close a cycle)."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        # union by rank: hang the shorter tree under the taller one, so tree
        # height stays O(log n) even without path compression.
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True

    def connected(self, a, b):
        return self.find(a) == self.find(b)

    def groups(self):
        """Return the sets as sorted lists, ordered by their smallest member."""
        by_root = {}
        for x in self.parent:
            by_root.setdefault(self.find(x), []).append(x)
        return sorted((sorted(g) for g in by_root.values()), key=lambda g: g[0])
