#!/usr/bin/env python3
"""
build_and_diagnose.py — Runs `buildozer android debug`, then automatically
finds and prints the real underlying error if it fails, or confirms and
locates the APK if it succeeds. This removes the need to manually scroll
through thousands of lines of build log looking for the actual failure.
"""
import subprocess
import sys
import glob
import os
import re

LOG_FILE = "build_output.log"

ERROR_PATTERNS = [
    re.compile(r"error:", re.IGNORECASE),
    re.compile(r"Traceback \(most recent call last\)"),
    re.compile(r"Command failed"),
    re.compile(r"fatal error"),
    re.compile(r"ModuleNotFoundError"),
    re.compile(r"ImportError"),
    re.compile(r"BUILD FAILED"),
    re.compile(r"ninja: build stopped"),
]

CONTEXT_BEFORE = 5
CONTEXT_AFTER = 15


def run_build():
    """Runs buildozer, streaming output live AND saving it to LOG_FILE."""
    print("=" * 70)
    print("Starting buildozer android debug ...")
    print("=" * 70, flush=True)

    with open(LOG_FILE, "w", encoding="utf-8", errors="replace") as f:
        process = subprocess.Popen(
            ["buildozer", "-v", "android", "debug"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in process.stdout:
            print(line, end="")       # live output in the Actions log
            f.write(line)             # saved copy for post-analysis
        process.wait()
        return process.returncode


def find_apk():
    matches = glob.glob("bin/*.apk")
    return matches


def print_diagnostics():
    """Scans the saved log for the first real error and prints it with
    surrounding context, instead of buildozer's generic outer failure
    message, which is rarely the actual cause."""
    if not os.path.exists(LOG_FILE):
        print("No log file was produced — nothing to diagnose.")
        return

    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    found_any = False
    for i, line in enumerate(lines):
        for pattern in ERROR_PATTERNS:
            if pattern.search(line):
                found_any = True
                start = max(0, i - CONTEXT_BEFORE)
                end = min(len(lines), i + CONTEXT_AFTER)
                print("\n" + "=" * 70)
                print(f"POSSIBLE ROOT CAUSE found at log line {i + 1} "
                      f"(matched: {pattern.pattern!r})")
                print("=" * 70)
                print("".join(lines[start:end]))
                break  # move to next line once we've reported this hit

    if not found_any:
        print("\n" + "=" * 70)
        print("No recognizable error pattern found in the log.")
        print("Printing the last 60 lines instead:")
        print("=" * 70)
        print("".join(lines[-60:]))


def main():
    returncode = run_build()
    apks = find_apk()

    print("\n" + "=" * 70)
    print("BUILD SUMMARY")
    print("=" * 70)
    print(f"buildozer exit code: {returncode}")
    print(f"APK files found in bin/: {apks if apks else 'NONE'}")

    if returncode != 0 or not apks:
        print("\nBuild did NOT produce an APK. Scanning log for the real error...\n")
        print_diagnostics()
        sys.exit(1)
    else:
        print(f"\nSuccess — APK ready at: {apks[0]}")
        sys.exit(0)


if __name__ == "__main__":
    main()
