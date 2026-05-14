document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-bs-toggle='tooltip']").forEach((el) => {
        new bootstrap.Tooltip(el);
    });

    document.querySelectorAll(".auto-dismiss").forEach((alert) => {
        window.setTimeout(() => {
            bootstrap.Alert.getOrCreateInstance(alert).close();
        }, 4500);
    });

    document.querySelectorAll(".needs-validation").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });
});
