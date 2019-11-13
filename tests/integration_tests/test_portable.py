import os
import sys
import subprocess  # nosec
from .screen_analysis import analyze

def test_portable(dash_duo, tmp_path):
    # Build a portable webviz from config file
    pages = [
        "inplacevolumesonebyone",
        "reservoirsimulationtimeseriesonebyone",
        "inplacevolumes",
        "parameterdistribution",
        "parametercorrelation",
        "last_page",
    ]
    appdir = tmp_path / "app"
    imgdir = os.path.dirname(os.path.abspath(__file__)) + "/screenshots"
    subprocess.call(  # nosec
        ["webviz", "build", "reek_example.yaml", "--portable", appdir], cwd="examples"
    )
    # Remove Talisman
    fn = appdir / "webviz_app.py"
    with open(fn, "r") as f:
        lines = f.readlines()
    with open(fn, "w") as f:
        for line in lines:
            if not line.strip("\n").startswith("Talisman"):
                f.write(line)
    # Import generated app
    sys.path.append(str(appdir))
    from webviz_app import app

    # Start and test app
    dash_duo.start_server(app)
    for page in pages:
        dash_duo.wait_for_element(f"#{page}").click()
        dash_duo.driver.save_screenshot(f'{imgdir}/staging/{page}.png')
        analyze(imgdir, page)
    assert dash_duo.get_logs() == [], "browser console should contain no error"
