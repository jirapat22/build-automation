"""
main.py - Entry point for the Hardware Build Automation tool.

CLI mode (default):   python main.py
Web form mode:        python main.py --ui
"""

import argparse
import re
import sys


# ======================================================================= #
# Workflow engine (shared by CLI and web)                                  #
# ======================================================================= #

def parse_serial_numbers(raw: str) -> list[str]:
    """Split a comma/newline-separated string into a clean list of SNs."""
    parts = re.split(r"[,\n]+", raw)
    return [p.strip() for p in parts if p.strip()]


def run_workflow(inputs: dict) -> dict:
    """
    Execute the full automation workflow.

    inputs keys:
        product_name, work_order, customer, num_units (int),
        serial_numbers (list[str])

    Returns a result dict with keys:
        work_order, product_name, customer, num_units, serial_numbers,
        parent_task ({id, key, url} | None),
        units (list of unit dicts),
        fatal_error (str | None)
    """
    from config import load_config
    from jira_service import JiraService
    from drive_service import DriveService

    result = {
        "work_order": inputs["work_order"],
        "product_name": inputs["product_name"],
        "customer": inputs["customer"],
        "num_units": inputs["num_units"],
        "serial_numbers": inputs["serial_numbers"],
        "parent_task": None,
        "units": [],
        "fatal_error": None,
    }

    # Load config --------------------------------------------------------
    try:
        config = load_config()
    except ValueError as exc:
        result["fatal_error"] = str(exc)
        return result

    # Initialise services ------------------------------------------------
    try:
        jira = JiraService(config)
    except Exception as exc:
        result["fatal_error"] = f"JIRA init failed: {exc}"
        return result

    try:
        drive = DriveService(config)
    except Exception as exc:
        result["fatal_error"] = f"Google Drive init/auth failed: {exc}"
        return result

    serial_numbers = inputs["serial_numbers"]

    # Step 1: Create parent JIRA task ------------------------------------
    try:
        parent = jira.create_parent_task(
            inputs["work_order"],
            inputs["product_name"],
            inputs["customer"],
            inputs["num_units"],
            serial_numbers,
        )
        result["parent_task"] = parent
        _log(f"  Created parent task: {parent['key']} ({parent['url']})")
    except Exception as exc:
        result["fatal_error"] = f"Failed to create parent JIRA task: {exc}"
        return result

    # Step 2: Process each serial number --------------------------------
    for sn in serial_numbers:
        unit: dict = {
            "serial_number": sn,
            "subtask": None,
            "drive_folder": None,
            "status": "pending",
            "error": None,
        }

        try:
            # 2a. Create sub-task
            _log(f"  [{sn}] Creating JIRA sub-task…")
            subtask = jira.create_subtask(
                parent["id"], sn,
                inputs["work_order"], inputs["product_name"], inputs["customer"],
            )
            unit["subtask"] = subtask
            _log(f"  [{sn}] Sub-task: {subtask['key']}")

            # 2b–e. Create Drive folder structure and copy templates
            _log(f"  [{sn}] Creating Drive folders and copying templates…")
            drive_link = drive.setup_serial_number(
                sn, inputs["work_order"], inputs["product_name"]
            )
            unit["drive_folder"] = drive_link
            _log(f"  [{sn}] Drive folder: {drive_link}")

            # 2f. Update sub-task with Drive link
            _log(f"  [{sn}] Updating sub-task with Drive link…")
            jira.update_subtask_with_drive_link(
                subtask["id"], sn,
                inputs["work_order"], inputs["product_name"], inputs["customer"],
                drive_link,
            )

            unit["status"] = "success"

        except Exception as exc:
            unit["status"] = "failed"
            unit["error"] = str(exc)
            _log(f"  [{sn}] ERROR: {exc}", error=True)

        result["units"].append(unit)

    # Step 3: Update parent description with all drive links ------------
    drive_links = {u["serial_number"]: u["drive_folder"] for u in result["units"]}
    try:
        _log("  Updating parent task with Drive links summary…")
        jira.update_parent_description(
            parent["id"],
            inputs["work_order"], inputs["product_name"], inputs["customer"],
            inputs["num_units"], serial_numbers, drive_links,
        )
    except Exception as exc:
        # Non-fatal — log but don't abort
        _log(f"  Warning: could not update parent description: {exc}", error=True)

    return result


def _log(msg: str, error: bool = False) -> None:
    """Simple progress logger (to stderr so it doesn't pollute web output)."""
    stream = sys.stderr if error else sys.stdout
    print(msg, file=stream, flush=True)


# ======================================================================= #
# CLI mode                                                                 #
# ======================================================================= #

def _prompt(label: str, validator=None, hint: str = "") -> str:
    while True:
        suffix = f" [{hint}]" if hint else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value:
            print("  ⚠  This field is required.")
            continue
        if validator:
            error = validator(value)
            if error:
                print(f"  ⚠  {error}")
                continue
        return value


def _validate_work_order(value: str) -> str | None:
    if not re.fullmatch(r"\d{8}", value):
        return "Work Order must be exactly 8 digits."
    return None


def _validate_positive_int(value: str) -> str | None:
    if not value.isdigit() or int(value) < 1:
        return "Please enter a positive integer."
    return None


def get_inputs_cli() -> dict:
    print("\n=== Hardware Build Automation ===\n")

    product_name = _prompt("Product Name", hint="e.g. POWER-1501-2-FA-PXIE")
    work_order   = _prompt("Work Order Number (8 digits)", _validate_work_order)
    customer     = _prompt("Customer Name")
    num_units    = int(_prompt("Number of Units", _validate_positive_int))

    # Serial number entry method
    print("\nHow would you like to enter Serial Numbers?")
    print("  1) One by one")
    print("  2) Paste a comma- or newline-separated list")
    method = _prompt("Choice", hint="1 or 2")
    while method not in ("1", "2"):
        print("  ⚠  Enter 1 or 2.")
        method = _prompt("Choice", hint="1 or 2")

    if method == "1":
        serial_numbers = []
        print(f"\nEnter {num_units} serial number(s). Press Enter after each.")
        for i in range(num_units):
            sn = _prompt(f"  Serial Number {i + 1}")
            serial_numbers.append(sn)
    else:
        print("\nPaste your serial numbers (comma- or newline-separated), then press Enter twice:")
        lines = []
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
        serial_numbers = parse_serial_numbers("\n".join(lines))

    # Validate count
    if len(serial_numbers) != num_units:
        print(
            f"\n  ⚠  Warning: you entered {len(serial_numbers)} serial number(s) "
            f"but specified {num_units} unit(s)."
        )
        answer = input("  Continue anyway? [y/N]: ").strip().lower()
        if answer != "y":
            print("  Aborted.")
            sys.exit(0)

    return {
        "product_name": product_name,
        "work_order": work_order,
        "customer": customer,
        "num_units": num_units,
        "serial_numbers": serial_numbers,
    }


def print_cli_summary(result: dict) -> None:
    print("\n" + "=" * 60)

    if result.get("fatal_error"):
        print(f"  ❌ Fatal error: {result['fatal_error']}")
        return

    pt = result["parent_task"]
    print(f"  ✅ Work Order:  {result['work_order']}")
    print(f"  📦 Product:     {result['product_name']}")
    print(f"  👤 Customer:    {result['customer']}")
    print(f"  🎫 JIRA Task:   {pt['key']}  {pt['url']}")

    units = result["units"]
    if units:
        print()
        col_sn  = max(len(u["serial_number"]) for u in units)
        col_sn  = max(col_sn, len("Serial Number"))
        col_st  = max(
            (len(u["subtask"]["key"]) if u["subtask"] else 0 for u in units),
            default=0,
        )
        col_st  = max(col_st, len("Sub-task"))
        col_drv = len("Drive Folder")

        header = (
            f"  {'Serial Number':<{col_sn}}  {'Sub-task':<{col_st}}  Drive Folder"
        )
        print(header)
        print("  " + "-" * (len(header) - 2 + col_drv + 4))

        for u in units:
            sn   = u["serial_number"]
            st   = u["subtask"]["key"] if u["subtask"] else "—"
            drv  = u["drive_folder"] or "—"
            icon = "✅" if u["status"] == "success" else "❌"
            print(f"  {sn:<{col_sn}}  {st:<{col_st}}  {drv}  {icon}")

    failed = [u for u in units if u["status"] == "failed"]
    if failed:
        print("\n  ❌ Failed units:")
        for u in failed:
            print(f"     • {u['serial_number']}: {u['error']}")

    print("=" * 60 + "\n")


def cli_main() -> None:
    inputs = get_inputs_cli()
    print("\nRunning…")
    result = run_workflow(inputs)
    print_cli_summary(result)


# ======================================================================= #
# Web / Flask mode                                                         #
# ======================================================================= #

def web_main() -> None:
    # Pre-flight: validate config + authenticate Drive before starting Flask
    # so the OAuth browser popup happens before the server is listening.
    print("Checking configuration…")
    try:
        from config import load_config
        config = load_config()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        sys.exit(1)

    print("Authenticating Google Drive (may open a browser on first run)…")
    try:
        from drive_service import DriveService
        DriveService(config)  # triggers OAuth if needed
    except Exception as exc:
        print(f"Google Drive auth failed: {exc}")
        sys.exit(1)

    print("Starting web server — open http://localhost:5000 in your browser.\n")

    from flask import Flask, render_template, request
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def form():
        return render_template("form.html")

    @app.route("/submit", methods=["POST"])
    def submit():
        product_name = request.form.get("product_name", "").strip()
        work_order   = request.form.get("work_order", "").strip()
        customer     = request.form.get("customer", "").strip()
        num_units_str = request.form.get("num_units", "0").strip()
        sns_raw      = request.form.get("serial_numbers", "").strip()

        errors = []

        if not product_name:
            errors.append("Product Name is required.")
        if not re.fullmatch(r"\d{8}", work_order):
            errors.append("Work Order must be exactly 8 digits.")
        if not customer:
            errors.append("Customer Name is required.")
        if not num_units_str.isdigit() or int(num_units_str) < 1:
            errors.append("Number of Units must be a positive integer.")
        if not sns_raw:
            errors.append("At least one Serial Number is required.")

        if errors:
            return render_template("form.html", errors=errors, form=request.form)

        num_units = int(num_units_str)
        serial_numbers = parse_serial_numbers(sns_raw)

        count_warning = None
        if len(serial_numbers) != num_units:
            count_warning = (
                f"Warning: {len(serial_numbers)} serial number(s) entered "
                f"but {num_units} unit(s) specified."
            )

        inputs = {
            "product_name": product_name,
            "work_order": work_order,
            "customer": customer,
            "num_units": num_units,
            "serial_numbers": serial_numbers,
        }

        result = run_workflow(inputs)
        return render_template("results.html", result=result, count_warning=count_warning)

    app.run(host="127.0.0.1", port=5000, debug=False)


# ======================================================================= #
# Entry point                                                              #
# ======================================================================= #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hardware Build Automation — creates JIRA tickets and Drive folders."
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch local web form UI instead of CLI prompts.",
    )
    args = parser.parse_args()

    if args.ui:
        web_main()
    else:
        cli_main()
