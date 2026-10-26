import io,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import installer,orbit_cli
class TestUpdater(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.old=os.environ.get('ORBIT_SETUP_HOME')
  os.environ['ORBIT_SETUP_HOME']=self.temp.name
  self.addCleanup(lambda:os.environ.pop('ORBIT_SETUP_HOME',None) if self.old is None else os.environ.__setitem__('ORBIT_SETUP_HOME',self.old))
  self.project=Path(self.temp.name)/'project';self.project.mkdir()
 def test_host_detection_is_read_only(self):
  result=orbit_cli.detect(str(self.project))
  self.assertEqual({x['host'] for x in result},set(orbit_cli.HOSTS))
  self.assertEqual({x['connected'] for x in result},{'NOT_VERIFIED'})
  self.assertEqual(list(self.project.iterdir()),[])
 def test_zip_escape_denied(self):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   z.writestr('orbit-universal-0.24.0/VERSION','0.24.0')
   z.writestr('orbit-universal-0.24.0/installer.py','pass')
   z.writestr('orbit-universal-0.24.0/../unsafe.py','unsafe')
  with self.assertRaises(ValueError):orbit_cli.validate_zip(out.getvalue(),'0.24.0')
 def test_vscode_uses_native_servers_preserves_other(self):
  d=self.project/'.vscode';d.mkdir()
  p=d/'mcp.json';p.write_text(json.dumps({'servers':{'existing':{'type':'http','url':'https://example.com'}}}))
  installer.install(installer.plan(self.project,['vscode'],scope='project'))
  self.assertIn('existing',json.loads(p.read_text())['servers'])
  self.assertEqual(json.loads(p.read_text())['servers']['orbit-core-native']['type'],'stdio')
  self.assertTrue((d/'mcp.json.orbit-backup').exists())
 def test_installs_stable_updater_without_path_mutation(self):
  installer.install(installer.plan(self.project,['codex'],scope='project'))
  h=Path(self.temp.name)/'.orbit-universal'
  self.assertTrue((h/'orbit_cli.py').is_file())
  self.assertTrue((h/'bin'/('orbit.cmd' if os.name=='nt' else 'orbit')).is_file())
if __name__=='__main__':unittest.main()
