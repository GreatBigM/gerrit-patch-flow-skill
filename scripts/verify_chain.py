#!/usr/bin/env python3
"""验证本地链是否与云端 revision 对齐（方案 C 校验）。

用法：
    python3 verify_chain.py <repo路径> <链尾revision> <revision1> <revision2> ...
    # 输出：每个 revision 是否为 HEAD 祖先（YES/NO），全 YES = 链完整对齐

也可用链尾验证：所有 revision 都应是链尾的祖先（云端线性前提）。
"""
import subprocess
import sys


def is_ancestor(repo, ancestor, descendant):
    r = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
    )
    return r.returncode == 0


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    repo = sys.argv[1]
    tail = sys.argv[2]
    revs = sys.argv[3:]
    ok = True
    for rev in revs:
        hit = is_ancestor(repo, rev, tail)
        ok = ok and hit
        print(f"{rev[:10]} {'YES' if hit else 'NO'}")
    print(f"\n结果: {'全部对齐 ✓（链完整）' if ok else '存在未对齐 ✗'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
