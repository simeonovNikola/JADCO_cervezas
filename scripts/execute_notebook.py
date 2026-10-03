"""Execute locally and review output structure before sharing safe aggregates."""

import argparse
import base64
import copy
import json
import os
import sys
import traceback
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from equinoxe import data_directory, load_tables, verify_manifest


def review_outputs(notebook, tables):
    forbidden = set()
    for table in tables.values():
        for column in ["sAddr1", "sLink"]:
            if column in table:
                forbidden.update(str(value) for value in table[column].dropna().unique() if len(str(value)) >= 10)
    rendered = []
    output_count = 0
    image_count = 0
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            output_count += 1
            if output.output_type == "error":
                raise ValueError("Notebook contains an error output.")
            if output.output_type == "stream":
                rendered.append(output.get("text", ""))
            for mime, value in output.get("data", {}).items():
                if mime in ["text/plain", "text/html", "text/markdown"]:
                    rendered.append(str(value))
                elif mime == "image/png":
                    image_count += 1
                else:
                    raise ValueError(f"Unreviewed output type: {mime}")
    text = "\n".join(rendered)
    if any(value in text for value in forbidden):
        raise ValueError("An output contains a private address or CRM link.")
    for token in ["previous_sRent", "sUnitCode</th>", "hUnit</th>", "sAddr1</th>", "sLink</th>"]:
        if token in text:
            raise ValueError("An output may expose a private row-level table.")
    if str(data_directory()) in text:
        raise ValueError("An output contains the machine-specific data path.")
    return {"outputs_reviewed": output_count, "aggregate_images": image_count,
            "address_link_scan_passed": True,
            "limitation": "Text scan and aggregate chart-source review; not an image OCR or universal privacy guarantee."}


def execute(share_aggregates=False):
    directory = data_directory()
    verify_manifest(directory)
    path = ROOT / "notebooks" / "equinoxe_analysis.ipynb"
    notebook = nbformat.read(path, as_version=4)
    original = copy.deepcopy(notebook)
    outputs_dir = ROOT / "private_outputs"
    outputs_dir.mkdir(exist_ok=True)
    runtime = outputs_dir / "runtime"
    runtime.mkdir(exist_ok=True)
    os.environ.setdefault("IPYTHONDIR", str(runtime / "ipython"))
    os.environ.setdefault("JUPYTER_CONFIG_DIR", str(runtime / "jupyter"))
    manager = KernelManager(kernel_name="python3", connection_file=str(runtime / "kernel.json"))
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client = NotebookClient(notebook, km=manager, timeout=300, resources={"metadata": {"path": str(ROOT)}})
    try:
        client.execute()
    except Exception:
        (outputs_dir / "execution_failure.log").write_text(traceback.format_exc(), encoding="utf-8")
        nbformat.write(notebook, outputs_dir / "failure.executed.ipynb")
        raise RuntimeError("Notebook execution failed; details are in ignored private_outputs/execution_failure.log.") from None
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    report = review_outputs(notebook, load_tables(directory))
    verify_manifest(directory)
    executed_path = outputs_dir / "equinoxe_analysis.executed.ipynb"
    nbformat.write(notebook, executed_path)
    image_index = 0
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            png = output.get("data", {}).get("image/png")
            if png:
                image_index += 1
                (outputs_dir / f"aggregate_chart_{image_index:02d}.png").write_bytes(base64.b64decode(png))
    if share_aggregates:
        for destination, executed in zip(original.cells, notebook.cells):
            if destination.cell_type == "code":
                destination.outputs = executed.outputs
                destination.execution_count = executed.execution_count
        nbformat.write(original, path)
    public_report = dict(report, clean_kernel=True, source_integrity_rechecked=True,
                         shared_aggregates=share_aggregates)
    print(json.dumps(public_report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--share-aggregates", action="store_true")
    arguments = parser.parse_args()
    execute(arguments.share_aggregates)
