#!/usr/bin/env python3
"""Deployment configuration checks: python3 -m unittest discover -s deploy/coolify -v.

Python 3.11+; no third-party Python packages. Docker validation is skipped when
Docker Compose is unavailable. These tests do not compile or deploy FigCraft.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


class DeploymentConfigTests(unittest.TestCase):
    def check_url(self, value: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(HERE / "check-public-url.sh"), value],
            capture_output=True, text=True, check=False,
        )

    def test_public_backend_urls(self) -> None:
        for url in ("wss://collab.example.com/", "wss://127.0.0.1/", "wss://collab.example.com:8443/"):
            with self.subTest(url=url):
                self.assertEqual(self.check_url(url).returncode, 0)

    def test_reject_secrets_and_unsupported_urls(self) -> None:
        for url in (
            "", "ws://collab.example.com/", "https://collab.example.com/",
            "wss://collab.example.com", "wss://collab.example.com/path/",
            "wss://collab.example.com/?key=do-not-log-this",
            "wss://user:password@collab.example.com/", "wss://collab.example.com/#token",
            "wss://collab.example.com/\nanything", " wss://collab.example.com/",
            "wss://collab.example.com/ ", "wss://collab.example.com/;echo bad",
        ):
            with self.subTest(url=url):
                result = self.check_url(url)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("do-not-log-this", result.stderr)
                self.assertNotIn("password", result.stderr)

    def test_shell_syntax(self) -> None:
        for path in HERE.glob("*.sh"):
            subprocess.run(["sh", "-n", str(path)], check=True)

    def test_server_is_private_and_persistent(self) -> None:
        with (HERE / "server.toml").open("rb") as stream:
            config = tomllib.load(stream)
        self.assertEqual(config["listen"], "0.0.0.0:47900")
        self.assertEqual(config["data"], "/data")
        self.assertIs(config["open_publish"], False)
        self.assertLess(config["max_file_mb"], 64)
        self.assertEqual(config["idle_days"], 0)
        self.assertNotIn("public_url", config)

    def test_entrypoint_preserves_arguments_and_private_umask(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            bindir = Path(folder)
            checker = bindir / "figcraft-check-url"
            shutil.copyfile(HERE / "check-public-url.sh", checker)
            checker.chmod(0o755)
            mock = bindir / "figcraft-server"
            mock.write_text(
                '#!/usr/bin/env python3\nimport json, os, sys\n'
                'print(json.dumps({"args": sys.argv[1:], "umask": os.umask(0)}))\n',
                encoding="utf-8",
            )
            mock.chmod(0o755)
            env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"],
                       FIGCRAFT_PUBLIC_URL="wss://collab.example.com/")
            args = ["links", "create", "synthetic-file", "--label", "A label with spaces"]
            result = subprocess.run(
                ["sh", str(HERE / "server-entrypoint.sh"), *args],
                env=env, text=True, capture_output=True, check=True,
            )
            output = json.loads(result.stdout)
            self.assertEqual(output["umask"], 0o077)
            self.assertEqual(output["args"], [
                "--config", "/etc/figcraft-server/server.toml",
                "--public-url", "wss://collab.example.com/", *args,
            ])

    def test_entrypoint_requires_url(self) -> None:
        env = dict(os.environ)
        env.pop("FIGCRAFT_PUBLIC_URL", None)
        result = subprocess.run(
            ["sh", str(HERE / "server-entrypoint.sh"), "serve"],
            env=env, text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FIGCRAFT_PUBLIC_URL", result.stderr)

    @unittest.skipUnless(shutil.which("docker"), "Docker is not installed")
    def test_compose_configuration(self) -> None:
        probe = subprocess.run(["docker", "compose", "version"], capture_output=True, check=False)
        if probe.returncode:
            self.skipTest("Docker Compose plugin is not installed")
        env = dict(os.environ, FIGCRAFT_PUBLIC_URL="wss://collab.example.invalid/")
        subprocess.run(
            ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "config", "--quiet"],
            cwd=ROOT, env=env, check=True,
        )


if __name__ == "__main__":
    unittest.main()
