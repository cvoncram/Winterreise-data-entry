// ===============================
//      CSV Preview Helper
// ===============================

async function initCsvPreview(cfg) {
    const input = document.getElementById(cfg.inputId);
    const previewContainer = document.getElementById(cfg.previewContainerId);

    previewContainer.innerHTML = `<em>No file uploaded yet.</em>`;
    previewContainer.classList.remove("has-data");

    async function loadPreview() {
        if (!input.files?.length) return;

        const form = new FormData();
        form.append("file", input.files[0]);

        if (cfg.hasHeaderId) {
            const chk = document.getElementById(cfg.hasHeaderId);
            form.append("has_header", chk?.checked ? "1" : "0");
        }

        try {
            const r = await fetch(cfg.previewEndpoint, { method: "POST", body: form });
            const data = await r.json();

            if (data.error) {
                previewContainer.innerHTML = `<p style="color:red">${data.error}</p>`;
            } else {
                previewContainer.innerHTML = data.html;
            }

            previewContainer.classList.add("has-data");
            if (cfg.onTokenReady) cfg.onTokenReady(data.token);
        } catch (err) {
            console.error("CSV preview error:", err);
            previewContainer.innerHTML = `<p style="color:red">Preview failed</p>`;
            previewContainer.classList.add("has-data");
        }
    }

    input.addEventListener("change", loadPreview);

    if (cfg.hasHeaderId) {
        const headerCheckbox = document.getElementById(cfg.hasHeaderId);
        headerCheckbox?.addEventListener("change", () => {
            if (input.files?.length) loadPreview();
        });
    }
}

