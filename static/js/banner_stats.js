(function () {
    "use strict";

    const bannerMatchup = document.getElementById("banner-matchup");

    function showPanel() {
        bannerMatchup.classList.remove("hidden");
    }

    function hidePanel() {
        bannerMatchup.classList.add("hidden");
    }

    function watchBanner() {
        const nameA = document.getElementById("fhud-name-a");
        const nameB = document.getElementById("fhud-name-b");
        if (!nameA || !nameB) return;

        const observer = new MutationObserver(() => {
            const textA = nameA.textContent.trim();
            const textB = nameB.textContent.trim();
            const hasA = textA !== "HOME" && textA !== "";
            const hasB = textB !== "AWAY" && textB !== "";
            (hasA || hasB) ? showPanel() : hidePanel();
        });

        observer.observe(nameA, { childList: true, characterData: true, subtree: true });
        observer.observe(nameB, { childList: true, characterData: true, subtree: true });
    }

    watchBanner();
})();
