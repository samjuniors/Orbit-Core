"""Real loopback integration checks for the opt-in local preview tool."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source/runtime'))
import orbit_mcp
import orbit_preview


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)/'todo';self.project.mkdir()
        (self.project/'index.html').write_text('TODO APP TEST',encoding='utf-8')
        self.previous=os.environ.get('ORBIT_PREVIEW_LOG_HOME')
        os.environ['ORBIT_PREVIEW_LOG_HOME']=str(Path(self.tmp.name)/'logs')
        self.addCleanup(self.restore_env)
        self.preview_id='todo-preview'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.args={'project_root':str(self.project),'preview_id':self.preview_id,
                   'command':[sys.executable,'-m','http.server',str(self.port),'--bind','127.0.0.1'],
                   'port':self.port,'health_path':'/'}
        self.addCleanup(lambda:orbit_preview.stop(self.project, {'preview_id':self.preview_id,'confirm_stop':True}))

    def restore_env(self):
        if self.previous is None:os.environ.pop('ORBIT_PREVIEW_LOG_HOME',None)
        else:os.environ['ORBIT_PREVIEW_LOG_HOME']=self.previous

    def test_preview_only_does_not_execute(self):
        result=orbit_preview.start(self.project,self.args)
        self.assertEqual(result['status'],'PREVIEW_ONLY')
        self.assertFalse((Path(self.tmp.name)/'logs').exists())

    def test_live_start_probe_log_stop(self):
        a={**self.args,'confirm_run':True}
        started=orbit_preview.start(self.project,a)
        self.assertEqual(started['status'],'READY',started)
        self.assertTrue(started['readiness']['healthy'])
        self.assertIn('127.0.0.1',started['preview_url'])
        ongoing=orbit_preview.status(self.project,{'preview_id':self.preview_id})
        self.assertEqual(ongoing['status'],'READY')
        self.assertEqual(orbit_preview.start(self.project,a)['status'],'ALREADY_RUNNING')
        self.assertEqual(orbit_preview.stop(self.project,{'preview_id':self.preview_id})['status'],'PREVIEW_ONLY')
        self.assertEqual(orbit_preview.stop(self.project,{'preview_id':self.preview_id,'confirm_stop':True})['status'],'STOPPED')
        self.assertEqual(orbit_preview.status(self.project,{'preview_id':self.preview_id})['status'],'NOT_MANAGED_BY_THIS_SESSION')

    def test_refuse_foreign_port(self):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',self.port));sock.listen(1)
            out=orbit_preview.start(self.project,{**self.args,'confirm_run':True})
            self.assertEqual(out['status'],'PORT_IN_USE')

    def test_command_and_path_validation(self):
        for bad in [['sh','-c','echo hi'], ['python','-c','print(1)'],['npm','install','bad']]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):orbit_preview.start(self.project,{**self.args,'command':bad})
        for bad in ['//example.com/path','/something?token=123','/a#b','']:
            with self.subTest(health=bad):
                with self.assertRaises(ValueError):orbit_preview.start(self.project,{**self.args,'health_path':bad})

    def test_stdio_mcp_lifecycle(self):
        env={**os.environ,'ORBIT_LOCAL_DB':str(Path(self.tmp.name)/'private.sqlite')}
        messages=[]
        def req(i,name,args):
            return {'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':name,'arguments':args}}
        messages=[req(1,'orbit_preview_start',self.args),req(2,'orbit_preview_start',{**self.args,'confirm_run':True}),
                  req(3,'orbit_preview_status',{'project_root':str(self.project),'preview_id':self.preview_id}),
                  req(4,'orbit_preview_stop',{'project_root':str(self.project),'preview_id':self.preview_id,'confirm_stop':True})]
        proc=subprocess.run([sys.executable,str(ROOT/'source/runtime/orbit_mcp.py')],input='\n'.join(json.dumps(m) for m in messages)+'\n',
                            text=True,capture_output=True,env=env,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        outputs=[json.loads(x) for x in proc.stdout.splitlines()]
        self.assertEqual(len(outputs),4)
        values=[json.loads(o['result']['content'][0]['text']) for o in outputs]
        self.assertEqual([v['status'] for v in values],['PREVIEW_ONLY','READY','READY','STOPPED'])
        self.assertTrue(all(not o['result']['isError'] for o in outputs))
        self.assertFalse(any('TODO APP TEST' in str(x) for x in values))


if __name__=='__main__':unittest.main()
