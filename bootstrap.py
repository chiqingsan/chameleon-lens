#!/usr/bin/env python3
"""项目启动器：检查 Python、维护 .venv、安装依赖并启动主程序。"""
import argparse
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"
REQUIREMENTS = ROOT / "requirements.txt"
APP_MODULE = "chameleon_lens"


def run(cmd, desc):
    print(f"[Chameleon Lens] {desc}...")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_python_version():
    if sys.version_info < (3, 11):
        print("[错误] 需要 Python 3.11 或更高版本。")
        print(f"[错误] 当前版本：{sys.version.split()[0]}")
        raise SystemExit(1)


def ensure_venv():
    if VENV_PY.exists():
        return
    print("[Chameleon Lens] 正在创建虚拟环境 .venv...")
    builder = venv.EnvBuilder(with_pip=True, clear=False)
    builder.create(VENV_DIR)


def ensure_dependencies():
    run([str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip"], "正在更新 pip")
    run([str(VENV_PY), "-m", "pip", "install", "-r", str(REQUIREMENTS)], "正在检查并安装依赖")


def main():
    parser = argparse.ArgumentParser(description="Chameleon Lens 启动器")
    parser.add_argument("--check-only", action="store_true", help="只检查环境和依赖，不启动覆盖层")
    args = parser.parse_args()

    ensure_python_version()
    ensure_venv()
    ensure_dependencies()

    if args.check_only:
        print("[Chameleon Lens] 环境检查完成。")
        return 0

    print("[Chameleon Lens] 启动覆盖层...")
    return subprocess.call([str(VENV_PY), "-m", APP_MODULE], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
