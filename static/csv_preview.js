async function initCsvPreview(cfg) {
    const input = document.getElementById(cfg.inputId);
    const previewContainer = document.getElementById(cfg.previewContainerId);

    // initial placeholder
    previewContainer.innerHTML = `<em>No file uploaded yet.</em>`;
    previewContainer.classList.remove("has-data");

    // helper to actually load preview from server
    async function loadPreview() {
        if (!input.files || !input.files.length) return;

        const form = new FormData();
        form.append("file", input.files[0]);

        // pass checkbox state if requested
        if (cfg.hasHeaderId) {
            const chk = document.getElementById(cfg.hasHeaderId);
            form.append("has_header", chk && chk.checked ? "1" : "0");
        }

        try {
            const r = await fetch(cfg.previewEndpoint, { method: "POST", body: form });
            const data = await r.json();

            if (data.error) {
                previewContainer.innerHTML = `<p style="color:red">${data.error}</p>`;
                previewContainer.classList.add("has-data");
                return;
            }

            previewContainer.innerHTML = data.html;
            previewContainer.classList.add("has-data");

            if (cfg.onTokenReady) cfg.onTokenReady(data.token);
        } catch (err) {
            previewContainer.innerHTML = `<p style="color:red">Preview failed</p>`;
            previewContainer.classList.add("has-data");
            console.error("preview error", err);
        }
    }

    // file input change -> load preview
    input.addEventListener("change", async () => {
        await loadPreview();
    });

    // if a hasHeaderId is provided, attach a change handler that reloads preview
    if (cfg.hasHeaderId) {
        const headerCheckbox = document.getElementById(cfg.hasHeaderId);
        if (headerCheckbox) {
            headerCheckbox.addEventListener("change", async () => {
                // only reload if a file is already chosen
                if (input.files && input.files.length) {
                    await loadPreview();
                }
            });
        } else {
            console.warn("initCsvPreview: hasHeaderId provided but element not found:", cfg.hasHeaderId);
        }
    }
}
