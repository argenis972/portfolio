import os

files = [
    "backend/tests/e2e/test_chaos_mild.py",
    "backend/tests/test_configuration.py",
    "backend/tests/test_robustness.py",
    "backend/tests/test_spam.py",
]

for f in files:
    if os.path.exists(f):
        with open(f, "rb") as fh:
            content = fh.read()
            if b"\r\n" in content:
                print(f"{f}: CRLF")
            elif b"\n" in content:
                print(f"{f}: LF")
            else:
                print(f"{f}: No line endings found")
    else:
        print(f"{f}: Not found")
