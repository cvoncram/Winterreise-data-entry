document.getElementById("sv_file").addEventListener("change", async function(e){
    const file = e.target.files[0];
    if(!file) return;

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

        if(!resp.ok){
            alert("Server error fetching previews");
            return;
        }

        const data = await resp.json();

        // Set preview text
        previewBeat.textContent = data.previews.beat || "(missing)";
        previewSpectral.textContent = data.previews.spectral || "(missing)";
        previewPower.textContent = data.previews.power || "(missing)";

        // Update dropdowns to match detected layers
        const beatSelect = document.getElementById("layer_beat");
        const spectralSelect = document.getElementById("layer_spectral");
        const powerSelect = document.getElementById("layer_power");

        if(data.detected_layers.beat) beatSelect.value = data.detected_layers.beat;
        if(data.detected_layers.spectral) spectralSelect.value = data.detected_layers.spectral;
        if(data.detected_layers.power) powerSelect.value = data.detected_layers.power;

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

    const previewContainer = document.getElementById("preview-container");
    const downloadPanel = document.getElementById("download-panel");
    const downloadLink = document.getElementById("download-link");

    previewContainer.innerHTML = "Processing...";
    downloadPanel.style.display = "none";

    try {
        const resp = await fetch("/sv-to-mei/process", {
            method:"POST",
            body:formData
        });

        if(!resp.ok){
            const err = await resp.json();
            previewContainer.innerHTML = `<div class="error">Error: ${err.detail}</div>`;
            return;
        }

        const data = await resp.json();
        const token = data.token;

        const previewResp = await fetch("/sv-to-mei/preview", {
            method:"POST",
            body: new URLSearchParams({token})
        });

        if(!previewResp.ok){
            previewContainer.innerHTML = "<div class='error'>Failed to fetch preview</div>";
            return;
        }

        const previewData = await previewResp.json();

        // Wrap preview in <pre> and ensure word-break
        previewContainer.innerHTML = `<pre style="white-space:pre-wrap; word-break:break-word; max-height:400px; overflow:auto;">${previewData.html}</pre>`;

        const downloadBtn = document.getElementById("download-btn");
        downloadBtn.onclick = () => {
            window.location = `/sv-to-mei/download/${token}`;
        };
        downloadPanel.style.display = "block";

    } catch(err){
        previewContainer.innerHTML = `<div class="error">Unexpected error: ${err}</div>`;
        console.error(err);
    }
});
