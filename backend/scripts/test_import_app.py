import importlib, traceback

try:
    import app
    print('OK', app)
except Exception:
    traceback.print_exc()
