"""Creates responses for the web UI."""

from typing import Literal

from valentina.utils import random_string


def create_toast(
    msg: str,
    level: Literal[
        "success", "error", "warning", "info", "SUCCESS", "ERROR", "WARNING", "INFO"
    ] = "SUCCESS",
) -> str:
    """Create a toast.

    Args:
        msg: The message to display in the toast.
        level: The level of the toast.

    Returns:
        A string of HTML that displays a toast.
    """
    match level.upper():
        case "SUCCESS":
            color = "success"
            icon = "fa-solid fa-circle-check"
        case "ERROR":
            color = "danger"
            icon = "fa-solid fa-circle-exclamation"
        case "WARNING":
            color = "warning"
            icon = "fa-solid fa-triangle-exclamation"
        case "INFO":
            color = "info"
            icon = "fa-solid fa-circle-info"
        case _:
            msg = f"Invalid toast level: {level}"
            raise ValueError(msg)

    random_id = random_string(4)
    return f"""\
<div class="toast-container top-0 start-50 translate-middle-x mt-5 pt-5">
    <div class="toast {random_id} align-items-center text-bg-{color} border-0 "
            role="alert"
            aria-live="assertive"
            aria-atomic="true">
        <div class="d-flex">
            <div class="toast-body">
                <i class="{icon}"></i>&nbsp;&nbsp;{msg}
            </div>
            <button type="button"
                    class="btn-close btn-close-white me-2 m-auto"
                    data-bs-dismiss="toast"
                    aria-label="Close"></button>
        </div>
    </div>
</div>
<script>
    var toastR = document.querySelector('.{random_id}');
    var toastE = new bootstrap.Toast(toastR);
    toastE.show();
</script>
"""
