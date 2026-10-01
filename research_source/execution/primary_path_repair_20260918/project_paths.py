"""Preserve frozen project path spelling across the user's directory junction.

Scoped to the original runner/core module's Path binding, never pathlib globally.
All OS access still addresses the same file object. Unrelated paths are unchanged.
"""
from pathlib import Path
import os

NativePath = Path
LOGICAL = Path(r'C:\项目\LGM-GAME-Partner-Delivery-20260724')
PHYSICAL = Path(r'C:\项目\LGM\02_代码与实验\正式实验工程')

def require(value, message):
    if not value: raise RuntimeError(message)

def root_identity():
    require(LOGICAL.is_dir() and PHYSICAL.is_dir() and os.path.samefile(LOGICAL, PHYSICAL),
            'The declared project roots are no longer the same directory')
    require(NativePath.resolve(LOGICAL, strict=True) == PHYSICAL, 'Unexpected junction target')
    stat = PHYSICAL.stat()
    return {'logical': str(LOGICAL), 'physical': str(PHYSICAL), 'same_directory': True,
            'device': stat.st_dev, 'file_id': stat.st_ino}

def preserve_project_path(resolved):
    physical = NativePath(resolved)
    if not physical.is_relative_to(PHYSICAL):
        return physical
    root_identity()
    relative = physical.relative_to(PHYSICAL)
    logical = LOGICAL / relative
    old_parent, new_parent = logical, physical
    # New output files/directories are admitted through their nearest existing
    # parent; this creates nothing and rejects divergent existing identities.
    while not new_parent.exists():
        require(not old_parent.exists() and new_parent != PHYSICAL,
                'A prospective path has a divergent existing alias')
        old_parent, new_parent = old_parent.parent, new_parent.parent
    require(old_parent.exists() and os.path.samefile(old_parent, new_parent),
            'Project aliases address different file objects')
    require(NativePath.resolve(logical, strict=False) == physical,
            'Logical path resolves to a different destination')
    return logical

class FrozenProjectPath(type(Path())):
    """Native WindowsPath operations, with a checked historical project spelling."""
    def resolve(self, strict=False):
        resolved = NativePath.resolve(self, strict=strict)
        return type(self)(preserve_project_path(resolved))
