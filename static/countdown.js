(function () {
  var el = document.getElementById("countdownDisplay");
  var container = document.getElementById("headerCountdown");
  if (!el || !container) return;

  var dateStr = container.getAttribute("data-event-date");
  if (!dateStr) return;

  // Parse YYYY-MM-DD as start of that day in local timezone
  var target = new Date(dateStr + "T00:00:00");
  if (isNaN(target.getTime())) return;

  function format(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function update() {
    var now = new Date();
    var diff = target - now;

    if (diff <= 0) {
      el.textContent = "Today / Passed";
      return;
    }

    var days = Math.floor(diff / (24 * 60 * 60 * 1000));
    var rest = diff % (24 * 60 * 60 * 1000);
    var hours = Math.floor(rest / (60 * 60 * 1000));
    rest = rest % (60 * 60 * 1000);
    var minutes = Math.floor(rest / (60 * 1000));
    rest = rest % (60 * 1000);
    var seconds = Math.floor(rest / 1000);

    if (days > 0) {
      el.textContent = days + "d " + format(hours) + "h " + format(minutes) + "m " + format(seconds) + "s";
    } else {
      el.textContent = format(hours) + ":" + format(minutes) + ":" + format(seconds);
    }
  }

  update();
  setInterval(update, 1000);
})();
