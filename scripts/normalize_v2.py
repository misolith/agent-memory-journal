import sys
from pathlib import Path
from agent_memory.storage import init_memory_root, extract_id, make_memory_id, render_memory_item, utc_now_iso, split_claim_and_metadata
from agent_memory.models_v2 import MemoryItem

def normalize_memory(root):
    paths = init_memory_root(root)
    for core_file in paths.core_dir.glob('*.md'):
        content = core_file.read_text(encoding='utf-8', errors='ignore')
        lines = content.splitlines()
        new_lines = []
        changed = False
        category = core_file.stem[:-1] # decisions -> decision
        if category == 'capabilitie': category = 'capability'
        
        for line in lines:
            if not line.strip().startswith('- '):
                new_lines.append(line)
                continue
            
            mid = extract_id(line)
            if mid:
                new_lines.append(line)
                continue
            
            # No ID, add one
            changed = True
            claim, meta = split_claim_and_metadata(line)
            pinned = 'pinned:true' in meta
            
            item = MemoryItem(
                id=make_memory_id(category, claim),
                text=claim,
                category=category,
                tier='warm',
                state='active',
                source='import',
                created_at=utc_now_iso(),
                pinned=pinned
            )
            new_lines.append(render_memory_item(item))
            
        if changed:
            core_file.write_text('\n'.join(new_lines).rstrip() + '\n', encoding='utf-8')
            print(f"Normalized {core_file}")

if __name__ == "__main__":
    normalize_memory(sys.argv[1])
