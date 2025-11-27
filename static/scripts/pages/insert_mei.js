// ===============================
//        Insert MEI JS
// ===============================

let CSV_TOKEN = null;

// -------------------------------
// CSV Preview Initialization
// -------------------------------
initCsvPreview({
    inputId: "csv-upload",
    previewContainerId: "csv-preview",
    previewEndpoint: "/insert-mei/preview_csv",
    onTokenReady: (token) => {
        CSV_TOKEN = token;
        document.getElementById("csv-token").value = token;
        populateDropdowns(token);
    }
});

// -------------------------------
// Populate Column Dropdowns
// -------------------------------
async function populateDropdowns(token) {
    const form = new FormData();
    form.append("token", token);
    const r = await fetch("/insert-mei/csv_columns", { method: "POST", body: form });
    const data = await r.json();

    const columns = data.columns;
    const preselects = {
        tempo_col: columns[2] ?? "",
        dynam_col: columns[5] ?? "",
        annot_col: columns[3] ?? ""
    };

    for (const id in preselects) {
        const selectInput = document.getElementById(id);
        const wrapper = document.getElementById(id + "-wrapper");
        const optionsDiv = document.getElementById(id + "-options");
        optionsDiv.innerHTML = "";

        columns.forEach(col => {
            const opt = document.createElement("div");
            opt.textContent = col;
            opt.onclick = () => {
                selectInput.value = col;
                wrapper.querySelector(".custom-select-display").textContent = col;
            };
            optionsDiv.appendChild(opt);
        });

        // Preselect
        if (preselects[id]) {
            selectInput.value = preselects[id];
            wrapper.querySelector(".custom-select-display").textContent = preselects[id];
        }
    }

    document.getElementById("column-selects").style.display = "flex";
}

// -------------------------------
// Process MEI Insertion
// -------------------------------
document.getElementById("process-mei").addEventListener("click", async () => {
    const meiFile = document.getElementById("mei-file-upload").files[0];
    if (!CSV_TOKEN || !meiFile) return alert("Upload both CSV and MEI.");

    const form = new FormData();
    form.append("csv_token", CSV_TOKEN);
    form.append("mei_file", meiFile);
    form.append("tempo_col", document.getElementById("tempo_col").value);
    form.append("dynam_col", document.getElementById("dynam_col").value);
    form.append("annot_col", document.getElementById("annot_col").value);

    const r = await fetch("/insert-mei/process", { method: "POST", body: form });
    const data = await r.json();

    // Render MEI preview
    renderMEIPreview(data.preview_measures);

    // Show download button
    document.getElementById("download-container").innerHTML =
        `<a href="/insert-mei/download/${data.token}" download="modified.mei">
            <button type="button">Download MEI</button>
        </a>`;
});
