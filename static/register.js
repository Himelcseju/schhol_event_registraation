(function () {
  var baseInput = document.getElementById('base_amount');
  var extraInput = document.getElementById('extra_amount');
  var siteFeeInput = document.getElementById('site_fee');
  var totalDisplay = document.getElementById('totalDisplay');
  if (!baseInput || !extraInput || !totalDisplay) return;

  function updateTotal() {
    var base = parseInt(baseInput.value, 10) || 0;
    var extra = parseInt(extraInput.value, 10) || 0;
    var siteFee = siteFeeInput ? (parseInt(siteFeeInput.value, 10) || 0) : 0;
    extra = extra < 0 ? 0 : extra;
    totalDisplay.textContent = base + extra + siteFee;
  }

  extraInput.addEventListener('input', updateTotal);
  extraInput.addEventListener('change', updateTotal);
  updateTotal();
})();
