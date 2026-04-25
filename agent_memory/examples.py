from __future__ import annotations

EXAMPLE_SNIPPETS = {
    'init': "from agent_memory import Journal\nj = Journal(root='.')\nj.init_v2()",
    'write': "j.note_v2('Decision: keep AGENT hot set tiny', category='decision', importance='high')\nj.remember_v2('AGENT.md must stay small and pinned-only', category='constraint', pinned=True)",
    'session': "j.session_note('review-42', 'Pinned detection is too loose', category='gotcha', importance='high')",
    'recall': "from agent_memory.core_recall import recall_core\nhits = recall_core('.memory', 'pinned hot set', k=5)",
    'ingest': "from agent_memory.ingest import ingest_cycle\nreport = ingest_cycle('.memory')",
}


def render_examples() -> str:
    sections = ['# Examples', '']
    for name, snippet in EXAMPLE_SNIPPETS.items():
        sections.append(f'## {name}')
        sections.append('```python')
        sections.append(snippet)
        sections.append('```')
        sections.append('')
    return '\n'.join(sections).rstrip() + '\n'
