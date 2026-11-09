"""Bounded resource/port/tool checks, no Spark/JVM or resolver invocation."""
import json
from pathlib import Path
import socket
import sys
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.common.artifacts import read_json
from ml.common.hardware import resources


def main():
    root = Path(__file__).resolve().parents[1]
    config = read_json(root / "configs/environment.json")
    current = resources(root)
    enough = current["available_memory_bytes"] is not None and current["available_memory_bytes"] >= 4 * 1024**3 and current["free_disk_bytes"] >= 20 * 1024**3
    tools = (Path(config["java"]["home"]) / "bin/java.exe").is_file() and (Path(config["spark"]["home"]) / "bin/spark-submit.cmd").is_file()
    injected = any(os.environ.get(name) for name in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "SPARK_SUBMIT_OPTS", "PYSPARK_SUBMIT_ARGS"))
    port_free = False
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", 4040))
            port_free = True
        except OSError:
            pass
    print(json.dumps({"ready": bool(enough and tools and port_free and not injected), "resources": current, "port4040_free": port_free,
                      "unreviewed_jvm_options_present": injected,
                      "spark_executed": False, "minimum_available_ram_gib": 4}))
    return 0 if enough and tools and port_free and not injected else 2


if __name__ == "__main__":
    raise SystemExit(main())
