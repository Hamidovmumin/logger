// property-location.js faylının sonuna əlavə et və ya edit səhifəsində işlət:

document.addEventListener("DOMContentLoaded", function () {
    // Hidden və ya görünən inputlardan mövcud koordinatları oxuyuruq
    const latInput = document.getElementById("id_latitude"); // Sənin lat input ID-si
    const lngInput = document.getElementById("id_longitude"); // Sənin lng input ID-si

    if (latInput && lngInput && latInput.value && lngInput.value) {
        const currentLat = parseFloat(latInput.value);
        const currentLng = parseFloat(lngInput.value);

        // 1. Mövcud koordinatda markeri yaradırıq
        if (marker) {
            map.removeLayer(marker);
        }
        marker = L.marker([currentLat, currentLng], { draggable: true }).addTo(map);
        bindMarkerDragEvent();

        // 2. Xəritəni həmin mövcud koordinata fokuslayırıq
        map.setView([currentLat, currentLng], 14);

        // 3. ƏN VACİB HİSSƏ: Mövcud nöqtənin hansı GeoJSON poliqonuna düşdüyünü tapırıq!
        // Bunun üçün mövcud olan geoJsonLayer daxilində ağıllı axtarış dövrü işlədirik:
        if (geoJsonLayer) {
            geoJsonLayer.eachLayer(function (layer) {
                // Əgər nöqtə bu poliqonun daxilindədirsə
                if (layer.getBounds().contains([currentLat, currentLng])) {
                    const props = layer.feature.properties || {};
                    let areaName = props.name || props.village || props.qesebe || "";
                    let districtName = props["addr:district"] || props.district || props.rayon || "";

                    // Bayaq yazdığımız Universal Fallback mexanizmi (Abşeron/Binəqədi üçün)
                    if (!districtName && areaName) {
                        const lowerArea = areaName.toLowerCase();
                        if (lowerArea.includes("nübar") || lowerArea.includes("atyalı") || lowerArea.includes("hökməli")) {
                            districtName = "Abşeron rayonu";
                        } else if (lowerArea.includes("sulutəpə")) {
                            districtName = "Binəqədi rayonu";
                        }
                    }

                    // Backend-ə sorğu atıb mövcud elanın dropdown-larını avtomatik sinxron edirik
                    processAndValidateLocation(districtName, areaName);
                }
            });
        }
    }
});