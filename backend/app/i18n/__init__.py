"""Translation boundary.

THE INVARIANT: the graph, the database and the rules layer are English-only.
Citizen input is normalised to English once, on the way in (`understand`);
citizen-facing text is translated once, on the way out (`localize`), through a
persistent cache (`translator`).

Nothing in `app/graph/` or `app/rag/` should import from here.
"""
