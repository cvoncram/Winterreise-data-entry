// ===============================
//      MEI Preview Helper
// ===============================

// Renders MEI preview in boxes (first/last N measures)
function renderMEIPreview(measures) {
    const container = document.getElementById("mei-preview");
    if (!container) return;

    container.innerHTML = "<h4>Preview Measures</h4>";
    container.style.display = "block";

    if (!measures || measures.length === 0) {
        container.innerHTML += "<p>No measures to preview.</p>";
        return;
    }

    const section = (title, subset) => {
        const secDiv = document.createElement("div");

        const h5 = document.createElement("h5");
        h5.textContent = title;
        secDiv.appendChild(h5);

        const flexContainer = document.createElement("div");
        flexContainer.style.display = "flex";
        flexContainer.style.flexWrap = "wrap";
        flexContainer.style.gap = "10px";

        subset.forEach(m => {
            const box = document.createElement("div");
            box.style.border = "1px solid #385170";
            box.style.padding = "10px";
            box.style.background = "#9fd3c7";
            box.style.flex = "1 1 45%";
            box.style.overflowX = "auto";
            box.style.borderRadius = "6px";

            const pre = document.createElement("pre");
            pre.textContent = m;
            box.appendChild(pre);

            flexContainer.appendChild(box);
        });

        secDiv.appendChild(flexContainer);
        return secDiv;
    };

    // Split measures in first half / last half
    const first5 = measures.slice(0, 5);
    const last5 = measures.slice(-5);

    container.appendChild(section("First 5 Measures", first5));
    container.appendChild(section("Last 5 Measures", last5));
}
