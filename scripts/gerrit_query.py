#!/usr/bin/env python3
"""Gerrit change 批量查询工具 — 拿最新 revision + parent + status。

用法：
    python3 gerrit_query.py <gerrit_host> <user> 213244 213266 213307 ...
    # 输出：number|status|ps|revision|parent

依赖：ssh + gerrit ssh command 可用（~/.ssh 免密配置）。
"""
import json
import subprocess
import sys


def query_change(host, user, change):
    """单个 change 查询，返回解析后的 dict。"""
    cmd = ["ssh", "-p", "29418", "-o", "ConnectTimeout=8",
           f"{user}@{host}", "gerrit", "query", f"change:{change}",
           "--format=JSON", "--current-patch-set"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "number" in d:
                ps = d.get("currentPatchSet", {})
                return {
                    "number": d.get("number"),
                    "status": d.get("status"),
                    "ps": ps.get("number"),
                    "revision": ps.get("revision"),
                    "parent": (ps.get("parents") or [None])[0],
                    "subject": d.get("subject", "")[:50],
                }
    except subprocess.TimeoutExpired:
        pass
    return {"number": change, "status": "QUERY_FAIL"}


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    host, user = sys.argv[1], sys.argv[2]
    changes = sys.argv[3:]
    for c in changes:
        d = query_change(host, user, c)
        if d["status"] == "QUERY_FAIL":
            print(f"{c}|QUERY_FAIL")
        else:
            print(f"{d['number']}|{d['status']}|ps{d['ps']}|"
                  f"{d['revision']}|parent={d['parent']}|{d['subject']}")


if __name__ == "__main__":
    main()
