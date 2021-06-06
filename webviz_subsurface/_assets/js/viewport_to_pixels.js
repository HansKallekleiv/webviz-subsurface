window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        view_height_to_pixels: function (_triggered) {
            return document.documentElement.clientHeight
        }
    }
});
