import os
import tempfile

# Isolate HERMES_HOME before any hermes import so config paths point at a tmp dir.
_TMP = tempfile.mkdtemp(prefix="hermes-tests-")
os.environ["HERMES_HOME"] = _TMP
