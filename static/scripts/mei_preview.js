// ===============================
//      MEI Preview Helper
// ===============================
function renderMEIPreview(measures) {
    const container = document.getElementById("mei-preview");
    if (!container) return;

    container.innerHTML = "<h4>Preview Measures</h4><p>Please ignore the xmlns attribute inside &ltmeasure&gt, it will not appear in the finished file.</p>";
    container.style.display = "block";

    if (!measures || measures.length === 0) {
        container.innerHTML += "<p>No measures to preview.</p>";
        return;
    }

    const section = (title, subset) => {
        const secDiv = document.createElement("div");
        secDiv.classList.add("mei-preview-section");

        const h5 = document.createElement("h5");
        h5.textContent = title;
        secDiv.appendChild(h5);

        const flexContainer = document.createElement("div");
        flexContainer.classList.add("mei-preview-flex");

        subset.forEach(m => {
            const box = document.createElement("div");
            box.classList.add("mei-preview-box");

            const pre = document.createElement("pre");
            pre.textContent = m;

            box.appendChild(pre);
            flexContainer.appendChild(box);
        });

        secDiv.appendChild(flexContainer);
        return secDiv;
    };

    const first4 = measures.slice(0, 4);
    const last4 = measures.slice(-4);

    container.appendChild(section("First Measures", first4));
    container.appendChild(section("Last Measures", last4));
}