import py_compile, sys

files = [
    "bot/__init__.py",
    "bot/logging_config.py",
    "bot/validators.py",
    "bot/client.py",
    "bot/orders.py",
    "cli.py",
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK : {f}")
    except py_compile.PyCompileError as e:
        errors.append((f, str(e)))
        print(f"  ERR: {f} — {e}")

print()
if errors:
    print("SYNTAX ERRORS FOUND:", len(errors))
    sys.exit(1)
else:
    print("ALL FILES: SYNTAX OK")
