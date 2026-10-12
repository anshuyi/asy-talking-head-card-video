import copy,importlib.util,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline',R/'scripts/pipeline.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Contract(unittest.TestCase):
 def setUp(self):
  self.d=json.loads((R/'examples/timeline.json').read_text(encoding='utf-8'));self.src={'duration':8,'width':720,'height':1280}
 def test_arbitrary_duration_and_scene_count(self):
  self.d['duration']=self.src['duration']=12.7;self.d['scenes'][0]['end']=12.7;m.validate(self.d,self.src,True)
 def test_unreviewed_cannot_be_final(self):
  with self.assertRaises(ValueError):m.validate(self.d,self.src,False)
 def test_overlap_rejected(self):
  self.d['captions'].append(copy.deepcopy(self.d['captions'][0]))
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True)
 def test_bad_crop_rejected(self):
  self.d['crop']['x']=100
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True)
 def test_nan_rejected(self):
  self.d['duration']=float('nan')
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True)
 def test_missing_tail_rejected(self):
  self.d['scenes'][0]['end']=7
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True)
 def test_hidden_captions_require_reason(self):
  self.d['captions'][0]['display']=False
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True)
 def test_no_audio_rejected(self):
  with self.assertRaises(ValueError):m.dimensions({'streams':[{'codec_type':'video','width':720,'height':1280}],'format':{'duration':8}})
 def test_av_offset_requires_normalization(self):
  with self.assertRaises(ValueError):m.dimensions({'streams':[{'codec_type':'video','width':720,'height':1280,'start_time':1},{'codec_type':'audio','start_time':0}],'format':{'duration':8}})
 def test_path_escape_rejected(self):
  for name in ['../final.mp4','..\\final.mp4','D:out.mp4','movie.txt']:
   with self.assertRaises(ValueError):m.filename(name)
 def test_source_evidence_required(self):
  del self.d['scenes'][0]['source_span']
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True)
 def test_reviewed_crop_required_for_render(self):
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True,True)
 def test_cannot_show_items_from_next_scene(self):
  self.d['scenes'][0]['items'][0]['at']=9
  with self.assertRaises(ValueError):m.validate(self.d,self.src,True)
if __name__=='__main__':unittest.main()
