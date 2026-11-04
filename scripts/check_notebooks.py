"""Validate notebook structure and compile every Python cell without downloading models."""
from pathlib import Path
import ast
import nbformat
root=Path(__file__).resolve().parents[1]
for path in sorted((root/'notebooks').glob('*.ipynb')):
 notebook=nbformat.read(path,as_version=4);nbformat.validate(notebook)
 for i,cell in enumerate(notebook.cells):
  if cell.cell_type=='code':ast.parse(cell.source,filename=f'{path.name}:cell{i}')
 print(path.name,'OK')
