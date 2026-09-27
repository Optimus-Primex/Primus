(function () {
  "use strict";

  var canvas = document.getElementById("latencyChart");
  if (!canvas) {
    return;
  }
  var ctx = canvas.getContext("2d");
  var url = canvas.getAttribute("data-checks-url");

  function clear() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  function message(text) {
    clear();
    ctx.fillStyle = "#667085";
    ctx.font = "14px system-ui, sans-serif";
    ctx.fillText(text, 12, 28);
  }

  function draw(checks) {
    clear();
    if (!checks.length) {
      message("No checks recorded yet.");
      return;
    }

    // The API returns newest-first; chart chronologically.
    var series = checks.slice().reverse();
    var padding = { top: 16, right: 12, bottom: 24, left: 40 };
    var width = canvas.width - padding.left - padding.right;
    var height = canvas.height - padding.top - padding.bottom;

    var latencies = series.map(function (check) {
      return check.latency_ms || 0;
    });
    var max = Math.max.apply(null, latencies.concat([1]));

    // Grid + axis labels.
    ctx.strokeStyle = "#e3e7ee";
    ctx.fillStyle = "#667085";
    ctx.font = "11px system-ui, sans-serif";
    ctx.lineWidth = 1;
    for (var i = 0; i <= 4; i += 1) {
      var y = padding.top + (height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + width, y);
      ctx.stroke();
      var label = Math.round(max - (max / 4) * i);
      ctx.fillText(label + " ms", 2, y - 2);
    }

    var slot = width / series.length;
    var barWidth = Math.max(1, slot - 1);
    series.forEach(function (check, index) {
      var value = check.latency_ms || 0;
      var barHeight = max === 0 ? 0 : (value / max) * height;
      var x = padding.left + index * slot;
      var y = padding.top + height - barHeight;
      ctx.fillStyle = check.success ? "#1a9d63" : "#d64545";
      ctx.fillRect(x, y, barWidth, barHeight);
    });
  }

  if (!url) {
    message("Chart data unavailable.");
    return;
  }

  message("Loading…");
  fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
    .then(function (response) {
      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }
      return response.json();
    })
    .then(function (data) {
      draw(data.checks || []);
    })
    .catch(function () {
      message("Unable to load check history.");
    });
})();
