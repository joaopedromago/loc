import errno
import json
import platform
import subprocess
import sys
import unittest

from loc_cli.offline import agent_policy
from tests.support import RuntimeFixture


@unittest.skipUnless(platform.system() == "Darwin", "macOS sandbox enforcement test")
class OfflineSandboxTests(unittest.TestCase):
    def test_agent_and_child_can_reach_gateway_but_not_other_sockets(self):
        with RuntimeFixture() as allowed, RuntimeFixture() as forbidden:
            port = allowed.server.server_port
            other = forbidden.server.server_port
            code = f'''import socket,json,subprocess,sys
def attempt(host,port):
 s=socket.socket(); s.settimeout(1)
 try: s.connect((host,port)); return 0
 except OSError as e: return e.errno
 finally: s.close()
print(json.dumps([attempt('127.0.0.1',{port}),attempt('127.0.0.1',{other}),attempt('192.0.2.1',443)]))
child="import socket; s=socket.socket(); s.connect(('127.0.0.1',{other}))"
print(subprocess.run([sys.executable,'-c',child],capture_output=True).returncode)
'''
            result = subprocess.run(["/usr/bin/sandbox-exec", "-p", agent_policy(port), sys.executable, "-c", code], capture_output=True, text=True)
        # Hosted CI/sandboxes can prohibit nested sandbox-exec. Report this as skipped, not a pass.
        if "sandbox_apply: Operation not permitted" in result.stderr:
            self.skipTest("Host prohibits nested sandbox-exec")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = result.stdout.splitlines()
        statuses = json.loads(rows[0])
        self.assertEqual(statuses[0], 0)
        self.assertIn(statuses[1], {errno.EPERM, errno.EACCES})
        self.assertIn(statuses[2], {errno.EPERM, errno.EACCES})
        self.assertNotEqual(int(rows[1]), 0)


if __name__ == "__main__":
    unittest.main()
