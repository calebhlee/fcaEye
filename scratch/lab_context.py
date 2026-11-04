"""Concept lattice of the lab formal context (people x MBTI letters).

Needs:  pip install concepts graphviz   (and the Graphviz program `dot`)
Run:    python lab_context.py
Output: lab_context.pdf and lab_context.png next to this file.
"""
from pathlib import Path

from concepts import Context

# --- 1. The data: incidence relation I (object -> set of attributes) ---------
I = {
    'Caleb': {'I', 'N', 'T', 'P'},
    'Britt': {'I', 'N', 'T', 'J'},
    'Christina': {'I', 'S', 'T', 'J'},
    'Sydney': {'E', 'S', 'F', 'P'},
    'Laura': {'E', 'N', 'T', 'J'},
}

# Fixed orders, so the table and the lattice always list things the same way.
# Attributes follow the opposite pairs, as on the slide.
G = list(I)                                  # objects
M = ['I', 'E', 'N', 'S', 'T', 'F', 'J', 'P']  # attributes

# --- 2. Build the formal context ----------------------------------------------
# `concepts` wants a Boolean table: one row per object, one True/False per
# attribute. True means (object, attribute) is in the relation I.
bools = [tuple(m in I[g] for m in M) for g in G]
context = Context(G, M, bools)

# --- 3. The concept lattice ----------------------------------------------------
# Every pair (extent, intent) that is closed under the two derivation
# operators is one formal concept; together they form the lattice.
lattice = context.lattice
print(f'{len(lattice)} concepts')
for extent, intent in lattice:
    print(sorted(extent), '<->', sorted(intent))

# --- 4. Draw it with labels ----------------------------------------------------
# By default `concepts` uses reduced labelling:
#   - an object name is written only at the lowest concept that contains it
#   - an attribute name is written only at the highest concept that has it
# This keeps the figure readable; the full sets can be read by following
# the lines down (extent) or up (intent).
graph = lattice.graphviz()

out_dir = Path(__file__).parent
graph.render(str(out_dir / 'lab_context'), format='pdf', cleanup=True)
graph.render(str(out_dir / 'lab_context'), format='png', cleanup=True)

# --- 5. Second figure: full labels, like the lattice on slide 11 --------------
# Here every node shows its complete extent (objects) and complete intent
# (attributes). We draw the graph ourselves with graphviz, because the
# library's default drawing uses reduced labelling only.
import graphviz


def as_text(items, order):
    """Join names in a fixed order; show the empty set as the symbol ∅."""
    names = [x for x in order if x in items]
    return ', '.join(names) if names else '∅'


full = graphviz.Digraph(
    graph_attr={'rankdir': 'BT',  # BT = bottom to top: top concept (all objects) on top
                'ranksep': '0.9', 'nodesep': '0.35', 'bgcolor': 'white'},
    node_attr={'shape': 'box', 'style': 'rounded,filled', 'fillcolor': '#eaf1f8',
               'color': '#4682b4', 'penwidth': '1.5', 'margin': '0.12,0.06'},
    # No arrowheads: in a lattice, "higher" already means "more general".
    edge_attr={'arrowhead': 'none', 'color': '#808080'},
)
for concept in lattice:
    extent_text = as_text(concept.extent, G)
    intent_text = as_text(concept.intent, M)
    # Objects in black, attributes in orange, so the two sets are easy to tell apart.
    full.node(str(concept.index),
              label=f'<<FONT POINT-SIZE="13">{extent_text}</FONT><BR/>'
                    f'<FONT POINT-SIZE="13" COLOR="#b45f06">{intent_text}</FONT>>')
for concept in lattice:
    # upper_neighbors = direct parents only, so each edge is a covering relation
    # and no redundant (transitive) lines are drawn.
    for parent in concept.upper_neighbors:
        full.edge(str(concept.index), str(parent.index))

full.render(str(out_dir / 'lab_context_full'), format='pdf', cleanup=True)
full.render(str(out_dir / 'lab_context_full'), format='png', cleanup=True)
