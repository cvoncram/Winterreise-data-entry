document.addEventListener("DOMContentLoaded", () => {
    // =========================
    // SV layer preview handler
    // =========================
    document.getElementById("sv_file").addEventListener("change", async function(e){
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("sv_file", file);

        const panel = document.getElementById("layer-preview-panel");
        const previewBeat = document.getElementById("preview-beat");
        const previewSpectral = document.getElementById("preview-spectral");
        const previewPower = document.getElementById("preview-power");

        panel.style.display = "none";

        try {
            const resp = await fetch("/sv-to-mei/preview-layers", {
                method: "POST",
                body: formData
            });

            if (!resp.ok) {
                alert("Server error fetching previews");
                return;
            }

            const data = await resp.json();

            previewBeat.textContent = data.previews.beat || "(missing)";
            previewSpectral.textContent = data.previews.spectral || "(missing)";
            previewPower.textContent = data.previews.power || "(missing)";

            const beatSelect = document.getElementById("layer_beat");
            const spectralSelect = document.getElementById("layer_spectral");
            const powerSelect = document.getElementById("layer_power");

            if (data.detected_layers.beat) beatSelect.value = data.detected_layers.beat;
            if (data.detected_layers.spectral) spectralSelect.value = data.detected_layers.spectral;
            if (data.detected_layers.power) powerSelect.value = data.detected_layers.power;

            panel.style.display = "block";
        } catch(err) {
            console.error("Preview error:", err);
            alert("Error fetching layer preview");
        }
    });

    // =====================
    // Submit handler
    // =====================
    document.getElementById("sv-to-mei-form").addEventListener("submit", async function(e){
        e.preventDefault();

        const form = e.target;
        const formData = new FormData(form);

        const previewContainer = document.getElementById("mei-preview");
        const downloadPanel = document.getElementById("download-panel");

        previewContainer.innerHTML = "Processing...";
        downloadPanel.style.display = "none";

        try {
            const resp = await fetch("/sv-to-mei/process", {
                method: "POST",
                body: formData
            });

            if (!resp.ok) {
                const err = await resp.json();
                previewContainer.innerHTML = `<div class="error">Error: ${err.detail}</div>`;
                return;
            }

            const data = await resp.json();
            const token = data.token;

            // ===========================
            // Display warnings (if any)
            // ===========================
            const warningPanel = document.getElementById("warning-panel");

            if (data.warnings && data.warnings.length > 0) {
                warningPanel.style.display = "block";
                warningPanel.innerHTML = data.warnings
                    .map(w => `<div>⚠️ ${w}</div>`)
                    .join("");
            } else {
                warningPanel.style.display = "none";
                warningPanel.innerHTML = "";
            }

            const previewResp = await fetch("/sv-to-mei/preview", {
                method: "POST",
                body: new URLSearchParams({token})
            });

            if (!previewResp.ok) {
                previewContainer.innerHTML = "<div class='error'>Failed to fetch preview</div>";
                return;
            }

            const previewData = await previewResp.json();
            console.log("DEBUG preview response:", previewData);

            if (previewData.measures && previewData.measures.length > 0) {
                renderMEIPreview(previewData.measures);
            } else {
                previewContainer.innerHTML = "<p>No MEI preview available yet. Please process the SV file first.</p>";
                previewContainer.style.display = "block";
            }

            const downloadBtn = document.getElementById("download-btn");
            downloadBtn.onclick = () => {
                window.location = `/sv-to-mei/download/${token}`;
            };
            downloadPanel.style.display = "block";

        } catch(err) {
            previewContainer.innerHTML = `<div class="error">Unexpected error: ${err}</div>`;
            console.error(err);
        }
    });

});