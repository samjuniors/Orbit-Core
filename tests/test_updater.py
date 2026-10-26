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

    def test_release_channel_prioritizes_highest_valid_asset(self):
        from unittest.mock import patch
        import json
        base='https://github.com/samjuniors/Orbit-Core-MCP/releases/download/'
        def release(v,pre,draft=False,assets=True):
            name='ORBIT-Universal-Setup-v'+v+'.zip'
            items=[{'name':name,'browser_download_url':base+'v'+v+'/'+name},
                   {'name':name+'.sha256','browser_download_url':base+'v'+v+'/'+name+'.sha256'}] if assets else []
            return {'tag_name':'v'+v,'draft':draft,'prerelease':pre,'assets':items,'html_url':base+'v'+v}
        choices=[release('0.24.0',True),release('0.23.0',True),release('1.0.0',False),
                 release('0.24.1',True,draft=True),release('0.24.2',True,assets=False)]
        with patch.object(orbit_cli,'download',return_value=json.dumps(choices).encode()):
            self.assertEqual(orbit_cli.latest('candidate')['version'],'0.24.0')
            self.assertEqual(orbit_cli.latest('stable')['version'],'1.0.0')

    def test_update_default_channel_is_candidate_and_no_side_effect(self):
        from unittest.mock import patch
        with patch.object(orbit_cli,'latest') as found:
            found.return_value={'version':'0.24.0','zip':'https://github.com/z','sha':'https://github.com/s','url':'https://github.com/release'}
            with patch.object(orbit_cli,'version',return_value='0.24.0'):
                self.assertEqual(orbit_cli.main(['update','--check']),0)
            found.assert_called_once_with('candidate')

if __name__=='__main__':unittest.main()
