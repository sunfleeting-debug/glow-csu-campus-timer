"""Verify delivered model files without loading or modifying the scene."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--all',action='store_true',help='Require all Release exchange files too');a=p.parse_args()
 rows=json.loads((ROOT/'models'/'manifest.json').read_text(encoding='utf-8'))['files'];missing=[];verified=[]
 for row in rows:
  path=ROOT/'models'/row['name']
  if not path.exists():missing.append(row['name']);continue
  h=hashlib.sha256()
  with path.open('rb') as f:
   for b in iter(lambda:f.read(4194304),b''):h.update(b)
  assert h.hexdigest()==row['sha256'] and path.stat().st_size==row['bytes'],row['name']
  verified.append(row['name'])
 assert verified, 'No model files found.'
 if a.all:assert not missing, 'Download missing files from Release: '+str(missing)
 print(json.dumps({'verified':verified,'optional_release_files_not_downloaded':missing,'all_available_files_match':True},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
