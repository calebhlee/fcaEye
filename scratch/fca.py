"""
Math of FCA

A formal context is a triple K = (G, M, I)
    G is a set of objects
    M is a set of attributes
    I is the incidence relation: A subset of G x M. 
    If (g, m) ∈ I, then "object g has attribute m"

Derivation operators:
For a set of objects A ⊆ G, 
A' is defined as the set of attributes in M that every object in A possesses.
    A' := {m ∈ M| gIm for all g ∈ A}
For a set of attributes B ⊆ M, 
B' is defined as the set of objects in G that possess every attribute in B.
    B' := {g ∈ G| gIm for all m ∈ B}
"""

G = {'Caleb', 'Britt', 'Christina', 'Sydney', 'Laura'}
M = {'I', 'E', 'N', 'S', 'T', 'F', 'J', 'P'}

I = {
    'Caleb': {'I', 'N', 'T', 'P'},
    'Britt': {'I', 'N', 'T', 'J'},
    'Christina': {'I', 'S', 'T', 'J'},
    'Sydney': {'E', 'S', 'F', 'P'},
    'Laura': {'E', 'N', 'T', 'J'}
}

def A_prime(A):
    '''A': attributes shared by every objects in A'''
    result = set(M)
    for a in A:
        result &= I[a]    # & means the elements that are in multiple sets (intersection)
    return result


def B_prime(B):
    '''B': objects that have every attribute in B'''
    result = set()
    for g in G:
        if B <= I[g]:
            result.add(g)
    return result


def closure(A):
    attributes = A_prime(A)
    objects = B_prime(attributes)
    return objects


def is_concept(A, B):
    return A_prime(A) == B and B_prime(B) == A


def subsets(S):
    """Return every subset of S as a list of sets."""
    result = [set()]                 # the empty set is the only subset of nothing
    for x in S:
        new_subset = []
        for old in result:
            new_subset.append(old | {x})   # same subset, with x added
        result = result + new_subset       # keep the old ones, add the new ones
    return result


def all_concepts():
    """Return every formal concept as a list of (extent, intent) pairs."""
    concepts = []
    for A in subsets(G):
        extent = closure(A)       # A''  (a closed set of objects)
        intent = A_prime(A)       # A'   (its matching attributes)
        pair = (extent, intent)
        if pair not in concepts:  # different A can give the same concept
            concepts.append(pair)
    return concepts
