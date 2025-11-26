// Renders MEI preview in boxes (first/last 10 measures)
function renderMEIPreview(measures) {
    const container = document.getElementById("mei-preview");
    container.innerHTML = "<h4>Preview Measures</h4>";
    container.style.display = "block";

    const section = (title, measuresSubset) => {
        const secDiv = document.createElement("div");
        const h5 = document.createElement("h5");
        h5.textContent = title;
        secDiv.appendChild(h5);

        const flexContainer = document.createElement("div");
        flexContainer.style.display = "flex";
        flexContainer.style.flexWrap = "wrap";
        flexContainer.style.gap = "10px";

        measuresSubset.forEach(m => {
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

    container.appendChild(section("First 10 Measures", measures.slice(0,10)));
    container.appendChild(section("Last 10 Measures", measures.slice(-10)));
}
