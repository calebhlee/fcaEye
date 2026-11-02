"""
Math of FCA

A formal context is a triple K = (G, M, I)
    G is a set of objects
    M is a set of attributes
    I is the incidence relation: A subset of G x M. 
    If (g, m) ∈ I, then "object g has attribute m"

Derivation operators:
For a set of objects A ⊆ G: A' = the set of attributes that every object in A has.
For a set of attributes B ⊆ M: B' = the set of objects that have every attribute in B.
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

def shared_attributes(A):
    '''A': attributes shared by every objects in A'''
    result = set(M)
    for g in A:
        result &= I[g]
    return result

def shared_objects(B):
    '''B': objects that have every attribute in B'''
    return {g for g in G if B <= I[g]}

def closure